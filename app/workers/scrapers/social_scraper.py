import urllib.parse
import xml.etree.ElementTree as ET

from app.workers.core.parent_scraper import ParentScraper
from app.workers.core.utils import save_json

# Proof of concept scraper using Reddit's RSS feed.
# Initial attempt with snscrape relied on deprecated/modified pushshift API.

# TODO implement HTML (if needed)


class SocialScraper(ParentScraper):
    BASE_URLS = ["https://www.reddit.com/search.rss?"]

    def build_url(self, base, query, language, region):
        """
        Options for params:
        - q: The search string (escaped via urlencode)
        - sort: 'new' (latest), 'relevance' (best match), 'top' (highest score)
        - t: 'all', 'day', 'week', 'month' (time filter)
        """
        params = {
            "q": query.text,
            "sort": "new",
            "t": "all",
            "hl": language,
            "gl": region,
            "ceid": f"{region}:{language.split('-')[0]}"
        }
        
        query_string = urllib.parse.urlencode(params)
        return f"{base}{query_string}"


    async def scrape(self, query, lan, region):

        all_results = []
        for link in self.BASE_URLS:
            url_ = self.build_url(link, query, lan, region)
            print(f"[SocialScraper] Fetching: {url_}")

            content, content_type = await self.load(url_)

            if not content:
                print(f"[SocialScraper] Abort scrape for {url_}")
                continue

            parsed = []
            if content_type == "xml":
                parsed = self.parse_rss(content)
            elif content_type == "html":
                parsed = self.parse_html(content)

            if parsed:
                all_results.extend(parsed)

        return all_results

    @staticmethod
    async def save_results(query, results):
        # prevents overwrite from multiple scrapers 
        # by including scraper name in filename
        filename = f"./Query_{query.id}_SocialScraper_results.json"
        save_json(results, filename)
        print(f"[SocialScraper] Results saved to {filename}")

    def parse_html(self, html):
        return []

    def parse_rss(self, content):
        articles = []
        try:
            # Reddit RSS uses the Atom namespace

            namespaces = {"atom": "http://www.w3.org/2005/Atom"}
            root = ET.fromstring(content)

            for entry in root.findall("atom:entry", namespaces):
                title = entry.findtext("atom:title", namespaces=namespaces)
                link_tag = entry.find("atom:link", namespaces=namespaces)
                url = link_tag.get("href") if link_tag is not None else ""

                # edge case: some entries are subreddit homepages or user profiles with
                # no relevant discussion content.
                # actual posts always contain '/comments/' in the url
                if "/comments/" not in url:
                    # skip subreddit homepages or user profiles
                    continue

                raw_content = entry.findtext("atom:content", namespaces=namespaces)
                published = entry.findtext("atom:updated", namespaces=namespaces)

                # following output format outlined in initial database schema
                articles.append(
                    {
                        "source_id": 1,  # eg. Reddit
                        "title": title,
                        "content": raw_content
                        if raw_content
                        else title,  # for now fallback to title if content is missing
                        "url": url,
                        "published_at": published,
                        "sentiment_label": None,
                        "sentiment_score": None,
                    }
                )
        except Exception as e:
            print(f"[SocialScraper] RSS Parsing error: {e}")

        return articles
