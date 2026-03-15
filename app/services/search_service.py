import asyncio
from app.schemas.search_request import SearchRequest
from app.schemas.search_response import (
    SearchResponse,
    SearchResultItem,
    SentimentScores,
)
import time
from datetime import datetime, timezone
from typing import List, Dict, Any
from app.workers.core.query import Query as ScraperQuery
from app.workers.scrapers.news_scraper import NewsScraper
from app.workers.scrapers.social_scraper import SocialScraper

class SearchService:
    def __init__(self):
        # Initialize scrapers once or per request?
        # Per request allows for fresh proxy rotation logic.
        self.platforms_map = {
            "News": NewsScraper,
            "Reddit": SocialScraper
        }

    async def execute_search(self, request: SearchRequest) -> SearchResponse:
        start_time = time.time()

        # 1. Convert frontend query to Worker Query object
        worker_query = ScraperQuery(text=request.query)

        # 2. Prepare tasks for requested platforms
        tasks = []
        for platform in request.platforms:
            scraper_class = self.platforms_map.get(platform)
            if scraper_class:
                # Instantiate and run (passing default lang/region for now)
                scraper_inst = scraper_class()
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


        #Keep this the same for now while testing

        # 2. TODO: Call ML models (ml/sentiment.py)

        # For now, we keep the mock logic here
        mock_results = [
            SearchResultItem(
                id="101",
                source="Reddit",
                content=f"Results for {request.query}",
                url="https://reddit.com",
                published_at=datetime.now(timezone.utc),
                sentiment=SentimentScores(label="Neutral", score=0.5),
            )
        ]

        execution_time = (time.time() - start_time) * 1000

        return SearchResponse(
            total_count=len(mock_results),
            execution_time_ms=round(execution_time, 2),
            results=mock_results,
        )

    def _map_to_schema(self, raw_item: Dict[str, Any]) -> SearchResultItem:
        """Translates Scraper dicts to SearchResultItem Pydantic models"""

        # Determine source string from source_id
        source_name = "Reddit" if raw_item.get("source_id") == 1 else "Google News"

        return SearchResultItem(
            id=str(hash(raw_item.get("url", ""))),  # Temporary unique ID
            source=source_name,
            title=raw_item.get("title"),
            content=raw_item.get("content", ""),
            url=raw_item.get("url", ""),
            # Note: Scrapers return strings, Pydantic wants datetime.
            # You might need dateutil.parser here later.
            published_at=datetime.now(),
            sentiment=None  # Placeholder for next sprint
        )

# Create a singleton instance to be used by the routes
search_service = SearchService()
