import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, request, jsonify, send_from_directory
import requests as req
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

JSTAGE_URL  = "https://api.jstage.jst.go.jp/searchapi/do"
CINII_URL   = "https://cir.nii.ac.jp/opensearch/articles"
CINII_APPID = os.environ.get("CINII_APPID", "9lEr5EcfpC4xCwFRGgGS")

NS = {
    "atom":       "http://www.w3.org/2005/Atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
    "prism":      "http://prismstandard.org/namespaces/basic/2.0/",
    "dc":         "http://purl.org/dc/elements/1.1/",
}

# ── Journal definitions ───────────────────────────────────────────────────
# ISSNs are searched against J-STAGE; 0 results = journal not indexed there.
# Wrong ISSN fails gracefully (returns []).

JOURNALS = [
    {"name": "経営史学",       "issn": "03869628", "category": "main"},
    {"name": "組織科学",       "issn": "02869713", "category": "main"},
    {"name": "日本経営学会誌", "issn": "18820131", "category": "main"},
    {"name": "社会経済史学",   "issn": "00380304", "category": "main"},
    {"name": "経済史研究",     "issn": "13441442", "category": "main"},
    {"name": "企業家研究",     "issn": "13490435", "category": "main"},
    {"name": "歴史と経済",     "issn": "03868338", "category": "main"},
]

KIYOU_KANSAI = [
    {"name": "経済論叢（京都大学）",       "issn": "00130273", "univ": "京都大学"},
    {"name": "大阪大学経済学",             "issn": "0473451X", "univ": "大阪大学"},
    {"name": "国民経済雑誌（神戸大学）",   "issn": "03873129", "univ": "神戸大学"},
    {"name": "同志社商学",                 "issn": "03872432", "univ": "同志社大学"},
    {"name": "立命館経営学",               "issn": "02876000", "univ": "立命館大学"},
    {"name": "立命館経済学",               "issn": "00355356", "univ": "立命館大学"},
    {"name": "関西大学商学論集",           "issn": "04513401", "univ": "関西大学"},
    {"name": "関西大学経済論集",           "issn": "04497554", "univ": "関西大学"},
    {"name": "関西学院大学商学論究",       "issn": "04549503", "univ": "関西学院大学"},
    {"name": "関西学院大学経済学論究",     "issn": "04540420", "univ": "関西学院大学"},
]

KIYOU_KANTO = [
    {"name": "経済学論集（東京大学）",     "issn": "00220973", "univ": "東京大学"},
    {"name": "社会科学研究（東京大学）",   "issn": "02876256", "univ": "東京大学"},
    {"name": "一橋論叢",                   "issn": "00182818", "univ": "一橋大学"},
    {"name": "経済研究（一橋大学）",       "issn": "00229733", "univ": "一橋大学"},
    {"name": "三田学会雑誌（慶應）",       "issn": "00266760", "univ": "慶應義塾大学"},
    {"name": "三田商学研究（慶應）",       "issn": "0544571X", "univ": "慶應義塾大学"},
    {"name": "早稲田商学",                 "issn": "09110518", "univ": "早稲田大学"},
    {"name": "学習院大学経済論集",         "issn": "04534654", "univ": "学習院大学"},
    {"name": "青山経営論集",               "issn": "09106863", "univ": "青山学院大学"},
    {"name": "中央大学商学研究年報",       "issn": "04492641", "univ": "中央大学"},
    {"name": "横浜経営研究",               "issn": "03888010", "univ": "横浜国立大学"},
]

ALL_JSTAGE_SOURCES = {
    "main":         JOURNALS,
    "kiyou_kansai": KIYOU_KANSAI,
    "kiyou_kanto":  KIYOU_KANTO,
}


# ── J-STAGE parser ────────────────────────────────────────────────────────

def parse_jstage_feed(xml_text: str, journal_name: str) -> list:
    results = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return results

    for entry in root.findall("atom:entry", NS):
        title_el = entry.find("atom:title", NS)
        title = (title_el.text or "").strip() if title_el is not None else ""

        link_el = entry.find("atom:link[@rel='alternate']", NS)
        url = link_el.get("href", "") if link_el is not None else ""

        authors = []
        for author in entry.findall("atom:author", NS):
            n = author.find("atom:name", NS)
            if n is not None and n.text:
                authors.append(n.text.strip())

        pub_date = entry.findtext("prism:publicationDate", "", NS)
        year = pub_date[:4] if pub_date and len(pub_date) >= 4 else ""

        summary_el = entry.find("atom:summary", NS)
        abstract = (summary_el.text or "").strip() if summary_el is not None else ""
        if len(abstract) > 400:
            abstract = abstract[:400] + "…"

        results.append({
            "title":   title,
            "authors": authors,
            "journal": journal_name,
            "year":    year,
            "url":     url,
            "abstract": abstract,
            "volume":  entry.findtext("prism:volume",       "", NS),
            "issue":   entry.findtext("prism:number",       "", NS),
            "page":    entry.findtext("prism:startingPage", "", NS),
            "source":  "J-STAGE",
        })
    return results


def search_jstage_journal(journal: dict, query: str, year_from: int, year_to: int) -> list:
    params = {
        "service":      "3",
        "text":         query,
        "issn":         journal["issn"],
        "pubyear_from": str(year_from),
        "pubyear_to":   str(year_to),
        "count":        "100",
        "start":        "1",
    }
    try:
        r = req.get(JSTAGE_URL, params=params, timeout=20)
        r.raise_for_status()
        return parse_jstage_feed(r.text, journal["name"])
    except Exception as e:
        print(f"J-STAGE error [{journal['name']}]: {e}")
        return []


# ── CiNii parser ──────────────────────────────────────────────────────────

def _str(v) -> str:
    if isinstance(v, list):
        return v[0] if v else ""
    return str(v) if v else ""


def parse_cinii_response(data: dict) -> list:
    results = []
    try:
        items = []
        for node in data.get("@graph", []):
            if isinstance(node, dict) and "items" in node:
                items = node["items"]
                break

        for item in items:
            title = _str(item.get("dc:title") or item.get("title", ""))

            creator_raw = item.get("creator") or item.get("dc:creator", [])
            if isinstance(creator_raw, str):
                authors = [creator_raw]
            elif isinstance(creator_raw, list):
                authors = []
                for c in creator_raw:
                    if isinstance(c, str):
                        authors.append(c)
                    elif isinstance(c, dict):
                        parts = [c.get("familyName", ""), c.get("givenName", "")]
                        name = " ".join(filter(None, parts))
                        if name:
                            authors.append(name)
            else:
                authors = []

            journal_name = _str(item.get("prism:publicationName") or item.get("publicationName", ""))
            date_raw = _str(item.get("prism:publicationDate") or item.get("datePublished", ""))
            year = date_raw[:4] if date_raw else ""
            url  = item.get("@id", "") or item.get("link", "")

            abstract_raw = item.get("description") or item.get("dc:description", "")
            abstract = _str(abstract_raw)
            if len(abstract) > 400:
                abstract = abstract[:400] + "…"

            results.append({
                "title":    title,
                "authors":  authors,
                "journal":  journal_name,
                "year":     year,
                "url":      url,
                "abstract": abstract,
                "volume":   "",
                "issue":    "",
                "page":     "",
                "source":   "CiNii",
            })
    except Exception as e:
        print(f"CiNii parse error: {e}")
    return results


def search_cinii(query: str, year_from: int, year_to: int, count: int = 100) -> list:
    params = {
        "q":      query,
        "count":  str(count),
        "start":  "1",
        "appid":  CINII_APPID,
        "format": "json",
        "from":   str(year_from),
        "until":  str(year_to),
    }
    try:
        r = req.get(CINII_URL, params=params, timeout=20)
        r.raise_for_status()
        return parse_cinii_response(r.json())
    except Exception as e:
        print(f"CiNii error: {e}")
        return []


# ── Flask routes ──────────────────────────────────────────────────────────

@app.route("/api/journals")
def get_journals():
    return jsonify({
        "main":         [j["name"] for j in JOURNALS],
        "kiyou_kansai": [j["name"] for j in KIYOU_KANSAI],
        "kiyou_kanto":  [j["name"] for j in KIYOU_KANTO],
    })


@app.route("/api/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "Query required"}), 400

    selected_main    = set(request.args.getlist("main"))
    selected_kansai  = set(request.args.getlist("kansai"))
    selected_kanto   = set(request.args.getlist("kanto"))
    year_from        = int(request.args.get("year_from", 1868))
    year_to          = int(request.args.get("year_to",   2025))
    sort             = request.args.get("sort",  "year_desc")
    include_cinii    = request.args.get("cinii", "false").lower() == "true"

    def pick(lst, selected):
        return [j for j in lst if not selected or j["name"] in selected]

    targets = (
        pick(JOURNALS,       selected_main)
        + pick(KIYOU_KANSAI, selected_kansai)
        + pick(KIYOU_KANTO,  selected_kanto)
    )

    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(search_jstage_journal, j, q, year_from, year_to): j["name"]
            for j in targets
        }
        if include_cinii:
            futures[executor.submit(search_cinii, q, year_from, year_to)] = "CiNii"

        for future in as_completed(futures):
            results.extend(future.result())

    if sort == "year_desc":
        results.sort(key=lambda x: x.get("year", ""), reverse=True)
    elif sort == "year_asc":
        results.sort(key=lambda x: x.get("year", ""))
    elif sort == "journal":
        results.sort(key=lambda x: x.get("journal", ""))

    return jsonify({"count": len(results), "results": results})


# Local dev: serve static files from public/
PUBLIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public")
if os.path.exists(PUBLIC_DIR):
    @app.route("/")
    def index_html():
        return send_from_directory(PUBLIC_DIR, "index.html")

    @app.route("/<path:path>")
    def static_file(path):
        return send_from_directory(PUBLIC_DIR, path)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
