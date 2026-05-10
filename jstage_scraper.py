"""
Scraper for J-STAGE (組織科学)
"""

from typing import List, Dict
from .base import BaseScraper
import urllib.parse


class JStageScraper(BaseScraper):
    """Scraper for 組織科学 (Organization Science - Japanese)"""

    BASE_URL = "https://www.jstage.jst.go.jp/AF06S010SryTopHyj"
    JOURNAL_CODE = "soshikikagaku"

    def get_journal_name(self) -> str:
        return "組織科学"

    def get_issn(self) -> str:
        return ""  # J-STAGE doesn't use CrossRef

    def search(self, keywords: List[str]) -> List[Dict[str, str]]:
        """Search 組織科学 for articles"""
        results = []

        search_query = " ".join(keywords)
        params = {
            'sryCd': self.JOURNAL_CODE,
            'kijiCd': '',
            'noVol': '',
            'noIssue': '',
            'kywd': search_query
        }

        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=self.timeout)
            response.raise_for_status()
        except Exception as e:
            print(f"J-STAGE request failed: {e}")
            return results

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'lxml')

        articles = soup.select('.article-list-item, .searchlist-item')

        for article in articles:
            try:
                title_elem = article.select_one('.article-title a, .searchlist-title a')
                title = title_elem.get_text(strip=True) if title_elem else "N/A"
                url = "https://www.jstage.jst.go.jp" + title_elem['href'] if title_elem and 'href' in title_elem.attrs else ""

                authors_elem = article.select('.author-name')
                authors = ", ".join([a.get_text(strip=True) for a in authors_elem]) if authors_elem else "N/A"

                year_elem = article.select_one('.year, .pub-date')
                year = year_elem.get_text(strip=True) if year_elem else "N/A"

                results.append({
                    'title': title,
                    'authors': authors,
                    'journal': self.get_journal_name(),
                    'year': year,
                    'url': url
                })
            except Exception as e:
                print(f"Error parsing article: {e}")
                continue

        return results
