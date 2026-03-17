import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from bs4 import BeautifulSoup

#SentimentScores,
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
        worker_query = ScraperQuery(text=request.query)

        tasks = []
        for platform in request.platforms:
            scraper_class = self.platforms_map.get(platform)
            if not scraper_class:
                continue

            # Setup config based on platform
            ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                  " (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
            if platform == "Reddit":
                ua = "linux:blackbird-backend:v1.0.0 (by /u/vtblackbird)"

            # Instantiate and add task
            scraper_inst = scraper_class(user_agent=ua)
            tasks.append(scraper_inst.run(worker_query, "en-US", "US"))

        # 3. Run all scrapers in parallel
        # This is critical so the user doesn't wait for them sequentially
        scraper_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 4. Flatten and Format results
        final_results: List[SearchResultItem] = []

        # Zip the platform names with the results so you know which is which
        for platform_name, platform_output in zip(request.platforms, scraper_results):
            print(f"\n--- [DEBUG] Raw Output for Platform: {platform_name} ---")

            if isinstance(platform_output, Exception):
                print(f"Error occurred in {platform_name}: {platform_output}")
                continue

            # This prints the whole list of dicts returned by that specific scraper
            print(platform_output)

            if isinstance(platform_output, list):
                for item in platform_output:
                    # Optional: Print individual items if the list is too long
                    # print(f"Processing item: {item.get('title')}")
                    final_results.append(self._map_to_schema(item))

        # --- LIMITING & SORTING LOGIC ---
        # Simple deduplication by URL
        seen_urls = set()
        unique_results = []
        for res in final_results:
            if res.url not in seen_urls:
                unique_results.append(res)
                seen_urls.add(res.url)
        final_results = unique_results
        # 1. Sort by published_at (Descending: Newest first)
        # Note: Since many are placeholders, this is a setup for when we add real dates.
        final_results.sort(key=lambda x: x.published_at, reverse=True)

        # 2. Apply the limit from the frontend request
        limit = request.limit if request.limit > 0 else 10
        limited_results = final_results[:limit]

        execution_time = (time.time() - start_time) * 1000

        return SearchResponse(
            total_count=len(limited_results),
            execution_time_ms=round(execution_time, 2),
            results=limited_results,
        )

        # 2. TODO: Call ML models (ml/sentiment.py)

    @staticmethod
    def _map_to_schema(raw_item: Dict[str, Any]) -> SearchResultItem:
        # 1. Clean HTML out of the content (especially for News)
        raw_content = raw_item.get("content", "")
        # Use BeautifulSoup to get just the text
        clean_content = BeautifulSoup(raw_content, "lxml").get_text(separator=" ")

        # 2. Truncate long content (especially for Reddit walls of text)
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

        # 4. Source Mapping
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
            published_at=parsed_date,  # Now a valid datetime object
            sentiment=None
        )

# Create a singleton instance to be used by the routes
search_service = SearchService()
