import asyncio
import random
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from bs4 import BeautifulSoup
from dateutil import parser

from app.schemas.search_request import SearchRequest
from app.schemas.search_response import (
    SearchResponse,
    SearchResultItem,
)
from app.workers.core.query import Query as ScraperQuery
from app.workers.scrapers.gov_scraper import GovScraper
from app.workers.scrapers.news_scraper import NewsScraper
from app.workers.scrapers.social_scraper import SocialScraper


class SearchService:
    def __init__(self) -> None:
        # Initialize scrapers once or per request?
        # Per request allows for fresh proxy rotation logic.
        self.platforms_map = {
            "News": NewsScraper,
            "Reddit": SocialScraper,
            "Gov": GovScraper
        }

    async def execute_search(self, request: SearchRequest) -> SearchResponse:
        start_time = time.time()

        # Ensure we use the new Dataclass structure correctly
        worker_query = ScraperQuery(text=request.query)

        tasks = []
        for platform in request.platforms:
            scraper_class = self.platforms_map.get(platform)
            if not scraper_class:
                continue

            ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                  " (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
            if platform == "Reddit":
                ua = "linux:blackbird-backend:v1.0.0 (by /u/vtblackbird)"

            # The new ParentScraper __init__ takes (proxies, user_agent)
            scraper_inst = scraper_class(proxies=[], user_agent=ua)

            # The new .run() orchestrates everything (setup -> scrape -> close)
            tasks.append(scraper_inst.run(worker_query, "en-US", "US"))

        scraper_results = await asyncio.gather(*tasks, return_exceptions=True)

        final_results: List[SearchResultItem] = []

        for platform_name, platform_output in zip(request.platforms, scraper_results):
            if isinstance(platform_output, Exception):
                print(f"Error in {platform_name}: {platform_output}")
                continue

            # CRITICAL: New scrapers might return None if they fail internally
            if platform_output is None:
                print(f"Platform {platform_name} returned no data.")
                continue

            if isinstance(platform_output, list):
                for item in platform_output:
                    # Defensive check: skip empty/malformed dicts
                    if not item or not isinstance(item, dict):
                        continue
                    final_results.append(self._map_to_schema(item))

        # --- LIMITING & SORTING LOGIC ---
        # Simple deduplication by URL
        seen_urls = set()
        unique_results = []
        for res in final_results:
            if res.url not in seen_urls:
                unique_results.append(res)
                seen_urls.add(res.url)

        #Shuffle for variety
        # This prevents the list from being dominated by a single scraper's results
        random.shuffle(unique_results)

        # 3. Apply the limit from the frontend request
        limit = request.limit if request.limit > 0 else 10
        limited_results = unique_results[:limit]

        # 4. Sort the final limited subset by date
        limited_results.sort(key=lambda x: x.published_at, reverse=True)

        execution_time = (time.time() - start_time) * 1000

        return SearchResponse(
            total_count=len(limited_results),
            execution_time_ms=round(execution_time, 2),
            results=limited_results,
        )

        # 2. TODO: Call ML models (ml/sentiment.py)

    @staticmethod
    def _map_to_schema(raw_item: Dict[str, Any]) -> SearchResultItem:
        #Clean HTML out of the content (Defensive Check added)
        raw_content = raw_item.get("content")

        # If content is None or not a string, fallback to empty string or title
        if not isinstance(raw_content, (str, bytes)):
            # Fallback to title if content is missing, or just an empty string
            raw_content = raw_item.get("title", "")

        # Now BeautifulSoup is guaranteed a string
        clean_content = BeautifulSoup(raw_content, "lxml").get_text(separator=" ")

        # 2. Truncate long content
        if len(clean_content) > 300:
            clean_content = clean_content[:297] + "..."

        raw_date = raw_item.get("published_at")
        parsed_date: datetime

        if not raw_date:
            # Fallback if the scraper found nothing
            parsed_date = datetime.now(timezone.utc)
        elif isinstance(raw_date, datetime):
            parsed_date = raw_date
        else:
            try:
                # dateutil handles the "Sat, 14 Mar..." format automatically
                parsed_date = parser.parse(str(raw_date))

                # Ensure it's timezone-aware for Pydantic
                if parsed_date.tzinfo is None:
                    parsed_date = parsed_date.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                # If parsing fails, use now() as a safety net
                parsed_date = datetime.now(timezone.utc)

        #Source Mapping
        source_map = {1: "Reddit", 2: "Google News", 3: "USA.gov"}
        source_id = raw_item.get("source_id")
        source_name = source_map.get(int(source_id) if source_id is not None
                                     else 0, "Web")

        return SearchResultItem(
            id=str(hash(raw_item.get("url", ""))),
            source=source_name,
            title=raw_item.get("title"),
            content=clean_content,
            url=raw_item.get("url", ""),
            published_at=parsed_date,
            sentiment=None
        )

# Create a singleton instance to be used by the routes
search_service = SearchService()
