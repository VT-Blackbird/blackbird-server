from app.workers.core.parent_scraper import ParentScraper


class SocialScraper(ParentScraper):

    async def scrape(self,query, lan, region):
        raise NotImplementedError
        url = f"https://example-social.com/"

        html = await self.fetch_content(url)

        return self.parse_posts(html)

    def parse_posts(self, html):
        return [{"post": "example"}]