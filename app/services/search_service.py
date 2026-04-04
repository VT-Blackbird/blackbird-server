import asyncio
import random
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from dateutil import parser
from sqlmodel import Session

from app.db.session import engine
from app.ml.cleaner import DataCleaner
from app.models import Article, Search, SearchSource
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
        self.cleaner = DataCleaner()

    async def execute_search(self, request: SearchRequest) -> SearchResponse:
        start_time = time.time()
        source_id_map = {"Reddit": 1, "News": 2, "Gov": 3}

        #Used to see if all sources are requested
        all_available = set(self.platforms_map.keys())
        requested = set(request.platforms)
        is_full_search = all_available.issubset(requested)

        #Open a database session
        with Session(engine) as session:
            #Create and save search record
            db_search = Search(query_text=request.query,
                               request_limit = request.limit,
                               all_sources_requested = is_full_search
                               )

            session.add(db_search)
            session.flush()
            #Link the source to the SearchSource bridge table

            if not is_full_search:
                for platform in request.platforms:
                    source_id = source_id_map.get(platform)
                    if source_id:
                        bridge = SearchSource(search_id=db_search.id,
                                              source_id=source_id)
                        session.add(bridge)

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

            for platform_name, platform_output in zip(request.platforms,
                                                      scraper_results):
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

                        # --- NEW CLEANING & FILTERING LOGIC ---
                        raw_text = item.get("content", "") or item.get("title", "")

                        # 1. Check Language (Filter out non-english languages)
                        if not self.cleaner.is_english(raw_text):
                            continue  # Skip non-English articles

                        # Clean the full content (Removes URLs, HTML, fix whitespace)
                        # Done before schema mapping
                        item["content"] = self.cleaner.clean(raw_text)
                        #Create the article db object after it is cleaned
                        db_article = Article(
                            title=item["title"],
                            content=item["content"],  # This is the FULL cleaned text
                            url=item["url"],
                            published_at=item.get("published_at"),
                            search_id=db_search.id,
                            source_id=source_id_map.get(platform_name, 0)
                        )
                        session.add(db_article)
                        final_results.append(self._map_to_schema(item))
            session.commit()



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

        #Apply the limit from the frontend request
        limit = request.limit if request.limit > 0 else 10
        limited_results = unique_results[:limit]

        #Sort the final limited subset by date
        limited_results.sort(key=lambda x: x.published_at, reverse=True)

        execution_time = (time.time() - start_time) * 1000
        print(limited_results)
        return SearchResponse(
            total_count=len(limited_results),
            execution_time_ms=round(execution_time, 2),
            results=limited_results,
        )



    @staticmethod
    def _map_to_schema(raw_item: Dict[str, Any]) -> SearchResultItem:

        content = raw_item.get("content")

        # If content is None or not a string, fallback to empty string or title
        if not isinstance(content, (str, bytes)):
            # Fallback to title if content is missing, or just an empty string
            content = raw_item.get("title", "")

        # 2. Truncate long content
        if len(content) > 300:
            content = content[:297] + "..."

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

        # 2. TODO: Call ML models (ml/sentiment.py)

        return SearchResultItem(
            id=str(hash(raw_item.get("url", ""))),
            source=source_name,
            title=raw_item.get("title"),
            content=content,
            url=raw_item.get("url", ""),
            published_at=parsed_date,
            sentiment=None
        )

# Create a singleton instance to be used by the routes
search_service = SearchService()
