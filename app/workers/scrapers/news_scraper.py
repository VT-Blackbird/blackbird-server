import urllib.parse
from typing import Any, Dict, List

from app.workers.core.parent_scraper import ParentScraper
from app.workers.core.query import Query
from app.workers.core.utils import save_json


class NewsScraper(ParentScraper):

    BASE_URLS = [
        "https://news.google.com/rss/search?"
    ]


    async def scrape(self, query: Query, lan: str, region: str) -> List[Dict[str, Any]]:

        all_results: List[Dict[str, Any]] = []

        for base in self.BASE_URLS:

            url = self.build_url(base, query, lan, region)
            print(f"[NewsScraper] Fetching RSS: {url}")

            # -----------------------------
            # STAGE 1A – RSS
            # -----------------------------
            raw = await self.fetch_rss(url)
            parsed: List[Dict[str, Any]] = []

            if raw:
                parsed = self.parse_rss(raw)

            # -----------------------------
            # STAGE 1B – HTML fallback
            # -----------------------------
            if not parsed:
                parsed = await self.html_fallback(query, lan, region)

            if not parsed:
                print("[NewsScraper] No articles found")
                continue


            # -----------------------------
            # Resolve Google News URLs
            # Basically Google News URL -> regular URL converter
            # -----------------------------
            resolved = await self.resolve_entries(parsed)

            # -----------------------------
            # STAGE 2 – Publisher scraping
            # -----------------------------
            enriched = await self.fetch_articles(resolved)

            # Fix values in enriched first
            start_index: int = len(all_results)
            all_results.extend(enriched)

            for i, (p, e) in enumerate(zip(parsed, enriched)):

                content_to_fill = p.get("content") or p.get("title")
                if not e.get('content') and content_to_fill:
                    idx:int = start_index + i
                    all_results[idx]["content"] = content_to_fill

        return all_results

    #Builds google news RSS url
    def build_url(self, base: str,
                  query: Query,
                  language: str,
                  region: str, page: int = 0) -> str:
        params: Dict[str, Any] = {
            "q": query.text,
            "hl": language,
            "gl": region,
            "ceid": f"{region}:{language.split('-')[0]}"
        }
        if page > 0:
            params["start"] = page * 10
        return f"{base}{urllib.parse.urlencode(params)}"


    @staticmethod
    async def save_results(query: Query, results: List[Any]) -> None:
        filename = f"./Query_{query.id}_NewsScraper_results.json"
        save_json(results, filename)
        print(f"[NewsScraper] Results saved to {filename}")
