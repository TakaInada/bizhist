const API_BASE = "";

// State
let journalData    = { main: [], kiyou_kansai: [], kiyou_kanto: [] };
let currentResults = [];
let currentQuery   = "";

// ── Init ─────────────────────────────────────────────────────────────────

async function init() {
  try {
    const res  = await fetch(`${API_BASE}/api/journals`);
    journalData = await res.json();
    renderHeroTags();
    renderAllCheckboxes();
  } catch (e) {
    console.error("Failed to load journals:", e);
  }
  bindEvents();
}

// ── Render sidebar checkboxes ─────────────────────────────────────────────

function checkboxList(names, groupClass, allChecked = true) {
  return names.map(n => `
    <label class="flex items-center gap-2 cursor-pointer text-sm hover:text-blue-600">
      <input type="checkbox" class="${groupClass} rounded" value="${n}" ${allChecked ? "checked" : ""}>
      <span class="leading-tight text-[0.8rem]">${n}</span>
    </label>`).join("");
}

function renderAllCheckboxes() {
  document.getElementById("chkMain").innerHTML   = checkboxList(journalData.main,         "chk-main");
  document.getElementById("chkKansai").innerHTML = checkboxList(journalData.kiyou_kansai, "chk-kansai", false);
  document.getElementById("chkKanto").innerHTML  = checkboxList(journalData.kiyou_kanto,  "chk-kanto",  false);
}

function renderHeroTags() {
  const all = [
    ...journalData.main.map(n => ({ n, cls: "bg-blue-50 text-blue-700 border-blue-100" })),
    ...journalData.kiyou_kansai.slice(0, 4).map(n => ({ n, cls: "bg-amber-50 text-amber-700 border-amber-100" })),
    ...journalData.kiyou_kanto.slice(0, 4).map(n => ({ n, cls: "bg-amber-50 text-amber-700 border-amber-100" })),
  ];
  document.getElementById("heroTags").innerHTML = all
    .map(({ n, cls }) => `<span class="px-3 py-1 bg-white border ${cls} rounded-full text-xs shadow-sm">${n}</span>`)
    .join("") + `<span class="px-3 py-1 bg-white border border-gray-200 text-gray-400 rounded-full text-xs shadow-sm">+ 紀要多数</span>`;
}

// ── Search ────────────────────────────────────────────────────────────────

function getChecked(cls) {
  return [...document.querySelectorAll(`.${cls}:checked`)].map(c => c.value);
}

async function doSearch(query) {
  query = (query || "").trim();
  if (!query) return;
  currentQuery = query;

  // Switch to results view
  document.getElementById("heroSection").classList.add("hidden");
  document.getElementById("resultsSection").classList.remove("hidden");
  document.getElementById("stickyHeader").classList.remove("hidden");
  document.getElementById("headerInput").value = query;

  document.getElementById("loadingSpinner").classList.remove("hidden");
  document.getElementById("resultsList").innerHTML = "";
  document.getElementById("statusBar").textContent = "";
  document.getElementById("errorBanner").classList.add("hidden");

  const params = new URLSearchParams({
    q:         query,
    year_from: document.getElementById("yearFrom").value,
    year_to:   document.getElementById("yearTo").value,
    sort:      document.getElementById("sortOrder").value,
    cinii:     document.getElementById("ciniiToggle").checked ? "true" : "false",
  });
  getChecked("chk-main").forEach(j   => params.append("main",   j));
  getChecked("chk-kansai").forEach(j => params.append("kansai", j));
  getChecked("chk-kanto").forEach(j  => params.append("kanto",  j));

  try {
    const res  = await fetch(`${API_BASE}/api/search?${params}`);
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    currentResults = data.results || [];
    renderResults(currentResults, data.count);
  } catch (e) {
    document.getElementById("errorBanner").classList.remove("hidden");
    document.getElementById("errorBanner").textContent = `エラー: ${e.message}`;
  } finally {
    document.getElementById("loadingSpinner").classList.add("hidden");
  }
}

// ── Render results ────────────────────────────────────────────────────────

function badgeHTML(r) {
  if (r.source === "CiNii") return `<span class="badge-cinii text-[0.65rem] font-semibold px-2 py-0.5 rounded-full">CiNii</span>`;
  const isKiyou = [...journalData.kiyou_kansai, ...journalData.kiyou_kanto].includes(r.journal);
  if (isKiyou) return `<span class="badge-kiyou text-[0.65rem] font-semibold px-2 py-0.5 rounded-full">紀要</span>`;
  return `<span class="badge-jstage text-[0.65rem] font-semibold px-2 py-0.5 rounded-full">J-STAGE</span>`;
}

function renderResults(results, count) {
  const statusBar = document.getElementById("statusBar");
  const list      = document.getElementById("resultsList");

  if (!results.length) {
    statusBar.textContent = "結果が見つかりませんでした。";
    list.innerHTML = `
      <div class="text-center py-24 text-gray-400">
        <svg class="w-14 h-14 mx-auto mb-4 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
        </svg>
        <p class="text-base">「${currentQuery}」に一致する論文が見つかりませんでした。</p>
        <p class="text-sm mt-1">対象ジャーナルを追加するか、CiNii検索を有効にしてください。</p>
      </div>`;
    return;
  }

  statusBar.innerHTML = `約 <strong class="text-gray-800">${count}</strong> 件`;

  list.innerHTML = results.map(r => {
    const authors  = r.authors?.length ? r.authors.join("・") : "著者情報なし";
    const metaParts = [
      r.journal  ? `<span class="font-medium text-gray-700">${r.journal}</span>` : "",
      r.year     || "",
      r.volume   ? `${r.volume}巻` : "",
      r.issue    ? `${r.issue}号` : "",
      r.page     ? `p.${r.page}` : "",
    ].filter(Boolean);
    const meta = metaParts.join(" &middot; ");
    const abstract = r.abstract
      ? `<p class="text-sm text-gray-500 mt-2 line-clamp-3">${r.abstract}</p>` : "";
    const linkEl = r.url
      ? `<a href="${r.url}" target="_blank" rel="noopener noreferrer"
            class="text-xs text-blue-500 hover:underline mt-2 inline-block">全文を見る →</a>` : "";

    return `
      <article class="bg-white rounded-xl border border-gray-200 px-5 py-4 hover:shadow-md transition-shadow">
        <div class="flex items-start justify-between gap-3">
          <a href="${r.url || "#"}" target="_blank" rel="noopener noreferrer"
             class="text-[1rem] font-semibold text-blue-700 hover:underline leading-snug flex-1">
            ${r.title || "(タイトルなし)"}
          </a>
          ${badgeHTML(r)}
        </div>
        <p class="text-sm text-gray-500 mt-1">${authors}</p>
        <p class="text-xs text-gray-400 mt-1">${meta}</p>
        ${abstract}
        ${linkEl}
      </article>`;
  }).join("");
}

// ── Client-side re-filter (without re-fetching) ───────────────────────────

function applyClientFilter() {
  const mainSel   = new Set(getChecked("chk-main"));
  const kansaiSel = new Set(getChecked("chk-kansai"));
  const kantoSel  = new Set(getChecked("chk-kanto"));
  const showCinii = document.getElementById("ciniiToggle").checked;
  const sort      = document.getElementById("sortOrder").value;

  const kansaiNames = new Set(journalData.kiyou_kansai);
  const kantoNames  = new Set(journalData.kiyou_kanto);

  let filtered = currentResults.filter(r => {
    if (r.source === "CiNii") return showCinii;
    if (kansaiNames.has(r.journal)) return kansaiSel.has(r.journal);
    if (kantoNames.has(r.journal))  return kantoSel.has(r.journal);
    return mainSel.has(r.journal);
  });

  if (sort === "year_desc") filtered.sort((a, b) => (b.year || "") > (a.year || "") ? 1 : -1);
  else if (sort === "year_asc") filtered.sort((a, b) => (a.year || "") > (b.year || "") ? 1 : -1);
  else if (sort === "journal")  filtered.sort((a, b) => (a.journal || "").localeCompare(b.journal || "", "ja"));

  renderResults(filtered, filtered.length);
}

// ── Events ────────────────────────────────────────────────────────────────

function bindEvents() {
  // Search triggers
  document.getElementById("heroBtn").addEventListener("click", () =>
    doSearch(document.getElementById("heroInput").value));
  document.getElementById("heroInput").addEventListener("keydown", e => {
    if (e.key === "Enter") doSearch(e.target.value);
  });
  document.getElementById("headerBtn").addEventListener("click", () =>
    doSearch(document.getElementById("headerInput").value));
  document.getElementById("headerInput").addEventListener("keydown", e => {
    if (e.key === "Enter") doSearch(e.target.value);
  });

  // Select all / none buttons
  document.querySelectorAll(".grp-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const cls    = { main: "chk-main", kansai: "chk-kansai", kanto: "chk-kanto" }[btn.dataset.group];
      const check  = btn.dataset.action === "all";
      document.querySelectorAll(`.${cls}`).forEach(c => c.checked = check);
      if (currentResults.length) applyClientFilter();
    });
  });

  // Sort change → re-render only
  document.getElementById("sortOrder").addEventListener("change", () => {
    if (currentResults.length) applyClientFilter();
  });

  // Journal checkbox changes → re-filter
  document.addEventListener("change", e => {
    const cls = e.target.className;
    if (cls.includes("chk-main") || cls.includes("chk-kansai") || cls.includes("chk-kanto")) {
      if (currentResults.length) applyClientFilter();
    }
    // CiNii toggle: re-fetch if turning on and no CiNii results cached
    if (e.target.id === "ciniiToggle") {
      if (e.target.checked && !currentResults.some(r => r.source === "CiNii") && currentQuery) {
        doSearch(currentQuery);
      } else if (currentResults.length) {
        applyClientFilter();
      }
    }
  });

  // Year changes → re-fetch
  ["yearFrom", "yearTo"].forEach(id => {
    document.getElementById(id).addEventListener("change", () => {
      if (currentQuery) doSearch(currentQuery);
    });
  });
}

init();
