from typing import Any, Dict, List

from app.workers.core.parent_scraper import ParentScraper
from app.workers.core.query import Query


class GovScraper(ParentScraper):
    # TODO - implement handling of multiple URLS
    BASE_URL = "temp"

    def build_url(self, query: Query, language: str, region: str) -> str:
        return f"{self.BASE_URL}{query}"

    async def scrape(self, query: Query, language: str, region: str) -> List[Any]:
        raise NotImplementedError
        url = self.build_url(query, language, region)

        html = await self.fetch_content(url)

        results = self.parse_results(html)

        return results

    def parse_results(self,html: str) -> List[Dict[str, str]]:
        # placeholder parser
        return [{"title": "example", "source": "demo"}]
