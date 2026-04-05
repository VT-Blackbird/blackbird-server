import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup

from app.workers.core.parent_scraper import ParentScraper
from app.workers.core.query import Query
from app.workers.core.utils import save_json


class GovScraper(ParentScraper):
    def build_url(
        self, base: str, query: Query, language: str, region: str, page: int = 0
    ) -> str:
        params: Dict[str, Any] = {
            "q": query.text,
            "hl": language,
            "gl": region,
            "ceid": f"{region}:{language.split('-')[0]}",
        }
        if page > 0:
            params["start"] = page * 10

        query_string = urllib.parse.urlencode(params)
        return f"{base}{query_string}"

    async def scrape(self, query: Query, lan: str, region: str) -> List[Dict[str, Any]]:
        all_results: List[Dict[str, Any]] = []

        # Fetch configuration from database
        source_cfg = self.get_source_config("USA.gov")

        if not source_cfg or source_cfg.id is None:
            print("[GovScraper] Source 'USA.gov' not found or has no ID in database.")
            return []

        if not source_cfg.is_enabled:
            print("[GovScraper] USA.gov source is currently disabled.")
            return []

        # Using the base_url from the database record
        url_ = self.build_url(
            base=source_cfg.base_url, query=query, language=lan, region=region
        )

        print(f"[GovScraper] Fetching: {url_}")
        result: Tuple[Optional[str], Optional[str]] = await self.load(url_)
        content, content_type = result
        
        if not content:
            print("abort scrape")
            return []
            
        parsed: Optional[List[Dict[str, Any]]] = None
        if content_type == "html":
            parsed = self.parse_html(content, source_cfg.id)
        elif content_type == "rss":
            parsed = self.parse_rss(content, source_cfg.id)
            
        if parsed:
            all_results.extend(parsed)
        elif parsed == []:
            print("No Content Found... Try refining Search Query")
            return []
        else:
            print(f"unsupported content type: {content_type}")
            return []

        return all_results

    @staticmethod
    async def save_results(query: Query, all_results: List[Dict[str, Any]]) -> None:
        filename = f"./Query_{query.id}_GovScraper_results.json"
        save_json(all_results, filename)
        print(f"[GovScraper] Results saved to {filename}")

    def parse_html(self, html: str, source_id: int) -> List[Dict[str, Any]]:
        articles: List[Dict[str, Any]] = []
        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception as e:
            print("BeautifulSoup error:", e)
            return articles
            
        title_tag = soup.title
        title = title_tag.string if title_tag and title_tag.string else None

        if title == "Access Denied":
            print("Access Denied")
            return articles
            
        usa_results = soup.select("div.content-block-item.result")
        if usa_results:
            for result in usa_results:
                title_el = result.select_one("h4.title a")
                desc_el = result.select_one("span.description")

                if not title_el:
                    continue

                title_text = title_el.get_text(strip=True)
                url = title_el.get("href")
                description = desc_el.get_text(strip=True) if desc_el else None

                articles.append(
                    {
                        "source_id": source_id,
                        "title": title_text,
                        "content": description,
                        "url": url,
                        "published_at": None,
                        "sentiment_label": None,
                        "sentiment_score": None,
                    }
                )
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