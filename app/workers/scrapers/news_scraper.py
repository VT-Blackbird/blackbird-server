import urllib.parse
from typing import Any, Dict, List

from app.models.source import Source
from app.workers.core.parent_scraper import ParentScraper
from app.workers.core.query import Query


class NewsScraper(ParentScraper):
    async def scrape(
        self, query: Query, lan: str, region: str, sources: List[Source]
    ) -> List[Dict[str, Any]]:
        all_results: List[Dict[str, Any]] = []

        for source in sources:
            if not source.is_enabled or source.id is None:
                continue

            url = self.build_url(source.base_url, query, lan, region)
            print(f"[NewsScraper] Fetching RSS: {url}")

            raw = await self.fetch_rss(url, source.id)
            parsed: List[Dict[str, Any]] = []
            if raw:
                parsed = self.parse_rss(raw, source.id)

            if not parsed:
                parsed = await self.html_fallback(query, lan, region, source.id)

            if not parsed:
                print(f"[NewsScraper] No articles found for source {source.name}")
                continue

            resolved = await self.resolve_entries(parsed)
            enriched = await self.fetch_articles(resolved)

            start_index: int = len(all_results)
            all_results.extend(enriched)

            for i, (p, e) in enumerate(zip(parsed, enriched)):
                content_to_fill = p.get("content") or p.get("title")
                if not e.get("content") and content_to_fill:
                    idx: int = start_index + i
                    all_results[idx]["content"] = content_to_fill

        return all_results

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
        return f"{base}{urllib.parse.urlencode(params)}"
