from app.workers.core.parent_scraper import ParentScraper


class GovScraper(ParentScraper):
    # TODO - implement handling of multiple URLS
    BASE_URL = "temp"

    def build_url(self, query, language, region):
        return f"{self.BASE_URL}{query}"

    async def scrape(self, query, language, region):
        raise NotImplementedError
        url = self.build_url(query, language, region)

        html = await self.fetch_content(url)

        results = self.parse_results(html)

        return results

    def parse_results(self, html):
        # placeholder parser
        return [{"title": "example", "source": "demo"}]
