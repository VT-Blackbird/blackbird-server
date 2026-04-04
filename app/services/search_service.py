import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from dateutil import parser
from sentence_transformers import SentenceTransformer, util
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
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    async def execute_search(self, request: SearchRequest) -> SearchResponse:
        start_time = time.time()
        source_id_map = {"Reddit": 1, "News": 2, "Gov": 3}

        # 1. Determine search scope
        all_available = set(self.platforms_map.keys())
        requested = set(request.platforms)
        is_full_search = all_available.issubset(requested)

        # 2. Initialize Search Record
        with (Session(engine) as session):
            db_search = Search(
                query_text=request.query,
                request_limit=request.limit,
                all_sources_requested=is_full_search
            )
            session.add(db_search)
            session.flush()  # Get the db_search.id

            if not is_full_search:
                for platform in request.platforms:
                    source_id = source_id_map.get(platform)
                    if source_id:
                        session.add(SearchSource(search_id=db_search.id,
                                                 source_id=source_id))

            # 3. Execute Scrapers concurrently
            worker_query = ScraperQuery(text=request.query)
            tasks = []
            for platform in request.platforms:
                scraper_class = self.platforms_map.get(platform)
                if scraper_class:
                    ua = ("linux:blackbird-backend:v1.0.0 (by"
                          " /u/vtblackbird)") if platform == "Reddit" else \
                        ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                         " (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
                    scraper_inst = scraper_class(proxies=[], user_agent=ua)
                    tasks.append(scraper_inst.run(worker_query, "en-US", "US"))

            scraper_results = await asyncio.gather(*tasks, return_exceptions=True)

            # 4. Filter, Clean, and Collect Raw Items
            temp_items = []
            for platform_name, platform_output in zip(request.platforms,
                                                      scraper_results):
                if isinstance(platform_output, (BaseException, Exception)
                              ) or platform_output is None:
                    continue


                for item in platform_output:
                    if not item or not isinstance(item, dict):
                        continue

                    # Language Filter & Cleaning
                    raw_text = item.get("content", "") or item.get("title", "")
                    if not self.cleaner.is_english(raw_text):
                        continue

                    item["content"] = self.cleaner.clean(raw_text)
                    item["source_id"] = source_id_map.get(platform_name, 0)
                    temp_items.append(item)

            final_results: List[SearchResultItem] = []

            # 5. ML Scoring & Database Persistence
            if temp_items:
                # Calculate embeddings for the batch
                query_emb = self.model.encode(request.query, convert_to_tensor=True)
                corpus_texts = [(f"{i['title']} "
                                 f"{i['content'][:200]}") for i in temp_items]
                corpus_embs = self.model.encode(corpus_texts, convert_to_tensor=True)
                cosine_scores = util.cos_sim(query_emb, corpus_embs)[0]

                for idx, item in enumerate(temp_items):
                    score = float(cosine_scores[idx])

                    # Update raw item so the mapper picks it up
                    item["relevance_score"] = score

                    # Create DB Model with the score
                    db_article = Article(
                        title=item["title"],
                        content=item["content"],
                        url=item["url"],
                        published_at=item.get("published_at"),
                        search_id=db_search.id,
                        source_id=item["source_id"],
                        relevance_score=score
                    )
                    session.add(db_article)

                    # Map to Response Schema
                    final_results.append(self._map_to_schema(item))

                session.commit()

        # 6. Deduplicate, Sort by Relevance, and Limit
        seen_urls = set()
        unique_results = []
        for res in final_results:
            if res.url not in seen_urls:
                unique_results.append(res)
                seen_urls.add(res.url)

        # High score at the top
        unique_results.sort(key=lambda x: (x.relevance_score or 0), reverse=True)

        limit = request.limit if request.limit > 0 else 10
        limited_results = unique_results[:limit]

        execution_time = (time.time() - start_time) * 1000

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
            sentiment=None,
            relevance_score=raw_item.get("relevance_score"),
        )

# Create a singleton instance to be used by the routes
search_service = SearchService()
