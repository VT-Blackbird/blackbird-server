import json
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup

from app.models.source import Source
from app.workers.core.parent_scraper import ParentScraper
from app.workers.core.query import Query

DateSearchResult = list[tuple[str, datetime]] | None

class GovScraper(ParentScraper):
    def build_url(
            self, base: str, query: Query, language: str, region: str
        ) -> str:
            params: Dict[str, Any] = {
                "hl": language,
                "gl": region,
                "ceid": f"{region}:{language.split('-')[0]}",
            }
            query_text_quoted = urllib.parse.quote_plus(query.text)
            other_params = urllib.parse.urlencode(params)

            return f"{base}{query_text_quoted}&{other_params}"
    def all_urls(self, base:str, query:Query, language:str, region:str,
            num_pages: int = 1) ->List[str]:
        """Creates dict of URLs to load, scrolls through first few pages in USA.gov"""
        url_base = self.build_url(base, query, language, region)
        url_list:List[str] = []
        p = 1
        while p <= num_pages:
            if p == 1:
                url_list.append(url_base)
            else:
                url_list.append(f"{url_base}&page={p}")
            p+=1
        return url_list

    async def scrape(
        self, query: Query, lan: str, region: str, sources: List[Source]
    ) -> List[Dict[str, Any]]:
        all_results: List[Dict[str, Any]] = []

        for source in sources:
            if not source.is_enabled or source.id is None:
                continue
            all_urls: List[str] = self.all_urls(base =source.base_url,
                                                query=query,
                                                language=lan,
                                                region = region,
                                                num_pages=2)
            for url_ in all_urls:
                print(f"[GovScraper] Fetching: {url_}")
                result: Tuple[Optional[str], Optional[str]] = await self.load(
                    url_, source.id
                )
                content, content_type = result

                if not content:
                    print(f"[GovScraper] No content for {source.name}")
                    continue

                parsed: Optional[List[Dict[str, Any]]] = None
                if content_type == "html":
                    print("[GovScraper] Parsing HTML content")
                    parsed = self.parse_html(content, source.id)
                elif content_type == "rss":
                    print("[GovScraper] Parsing RSS content")
                    parsed = self.parse_rss(content, source.id)

                if parsed:
                    all_results.extend(parsed)
                elif parsed == []:
                    print(f"[GovScraper] No content found for {source.name}")
        return all_results

    def parse_html(self, html: str, source_id: int) -> List[Dict[str, Any]]:
            articles: List[Dict[str, Any]] = []
            soup = BeautifulSoup(html, "lxml")

            # Now targeting the React props container
            react_div = soup.select_one('div[data-react-props]')

            if react_div:
                try:
                    props_str = react_div.get('data-react-props', '{}')
                    props = json.loads(props_str)

                    results_list = props.get('resultsData', {}).get('results', [])

                    for r in results_list:
                        title = r.get('title', '')
                        title = title.replace('<strong>', '').replace('</strong>', '')
                        desc = r.get('description', '')
                        desc = desc.replace('<strong>', '').replace('</strong>', '')
                        pub_date: datetime | None = self.parse_date(desc)
                        articles.append({
                            "source_id": source_id,
                            "title": title,
                            "content": desc,
                            "url": r.get('url'),
                            "published_at": pub_date,
                            "sentiment_label": None,
                            "sentiment_score": None,
                        })

                    if articles:
                        print(
                            f"[GovScraper] Successfully parsed {len(articles)} "
                            "results from React props"
                        )
                        return articles

                except Exception as e:
                    print(f"[GovScraper] Error parsing React JSON props: {e}")

            # Previous Implementation as secondary fallback
            print("[GovScraper] React props not found, falling back to CSS selectors")
            usa_results = soup.select("div.result.search-result-item")
            print(f"[GovScraper] Found {len(usa_results)} results in HTML content")
            
            if usa_results:
                for result in usa_results:
                    title_el = result.select_one(".result-title-label")
                    desc_el = result.select_one(".result-desc p")
                    url_el = result.select_one(".result-url-text")

                    if not title_el:
                        continue

                    articles.append({
                        "source_id": source_id,
                        "title": title_el.get_text(strip=True),
                        "content": desc_el.get_text(strip=True) if desc_el else None,
                        "url": url_el.get_text(strip=True) if url_el else None,
                        "published_at": None,
                        "sentiment_label": None,
                        "sentiment_score": None,
                    })
            return articles

    def parse_rss(self, content: str, source_id: int) -> List[Dict[str, Any]]:
        root = ET.fromstring(content)
        articles: List[Dict[str, Any]] = []
        for item in root.findall(".//item"):
            title = item.findtext("title")
            link = item.findtext("link")
            description = item.findtext("description")
            pub_date = item.findtext("pubDate")

            articles.append(
                {
                    "source_id": source_id,
                    "title": title,
                    "content": description,
                    "url": link,
                    "published_at": pub_date,
                    "sentiment_label": None,
                    "sentiment_score": None,
                }
            )
        return articles

    def _search_dates(self, text: str, settings:Dict[str,
        List[Any]])-> DateSearchResult:
        from dateparser.search import search_dates  # type: ignore[import-untyped]
        return search_dates(text, settings=settings)

    def parse_date(self, content:str)-> datetime | None:
        time_result = self._search_dates(content[:30].lower(),
                     settings={'REQUIRE_PARTS': ['month']})
        if time_result:
            time = time_result[0][1]
            # print("Found date in the provided text. ", time)
            return time
        else:
            # print("No date found in the provided text.")
            return None

