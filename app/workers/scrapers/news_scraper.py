import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from app.workers.core.query import Query
from app.workers.core.utils import save_json
from app.workers.core.parent_scraper import ParentScraper


# TODO implement HTML


class NewsScraper(ParentScraper):

    BASE_URLS = [
        "https://news.google.com/rss/search?"
    ]  # HTML Scraping is NOT STABLE, "https://search.yahoo.com/search?"]

    def build_url(self, base: str, query: Query, language:str, region:str,
                  page:int=0)->str:
        params: Dict[str, Any] = {
            "q": query.text,
            "hl": language,
            "gl": region,
            "ceid": f"{region}:{language.split('-')[0]}",
        }
        if page > 0:
            params["start"] = page * 10  # Google News shows 10 results per page

        query_string = urllib.parse.urlencode(params)
        return f"{base}{query_string}"

    async def scrape(self, query:Query, lan:str, region:str)->List[Dict[str, Any]]:
        all_results = []
        for link in NewsScraper.BASE_URLS:
            url_ = self.build_url(link, query, lan, region)
            print(f"[NewsScraper] Fetching: {url_}")
            result:Tuple[Optional[str], Optional[str]] = await self.load(url_)
            content, content_type =result
            parsed:List[Dict[str,str]] = []
            if not content:
                print("abort scrape")
                continue
            if content_type == "xml":
                parsed = self.parse_rss(content)
            if content_type == "html":
                parsed = self.parse_html(content)
            if parsed:
                all_results.extend(parsed)
        return all_results
    @staticmethod
    async def save_results(query: Query, results: List[Any]) -> None:
        # prevents overwrite from multiple scrapers
        # by including scraper name in filename
        filename = f"./Query_{query.id}_NewsScraper_results.json"
        save_json(results, filename)
        print(f"[NewsScraper] Results saved to {filename}")

    def parse_html(self, html:str)->List[Dict[str,str]]:
        soup = BeautifulSoup(html, "lxml")

        articles: List[Dict[str,str]]= []
        for article in soup.find_all("article"):
            title_tag = article.find("h3")
            if not title_tag:
                continue

            articles.append(
                {
                    "title": title_tag.get_text(strip=True),
                }
            )

        return articles
        # placeholder parser

    def parse_rss(self, content:str)-> List[Dict[str,Any]]:
        root = ET.fromstring(content)

        articles:List[Dict[str, Any]] = []
        for item in root.findall(".//item"):
            title = item.findtext("title")
            link = item.findtext("link")
            caption = item.findtext("description")
            pub_date = item.findtext("pubDate")

            articles.append(
                {
                    "source_id": 2,  #placeholder
                    "title": title,
                    "content": caption,
                    "url": link,
                    "published_at": pub_date,
                    "sentiment_label": None,
                    "sentiment_score": None
                }
            )

        return articles
