import asyncio
import hashlib
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Type
from uuid import UUID

from dateutil import parser
from sentence_transformers import SentenceTransformer, util
from sqlmodel import Session, desc, select
from tenacity import retry, stop_after_attempt, wait_exponential

from app.db.session import engine
from app.ml.cleaner import DataCleaner
from app.ml.NewsSentiment import NewsSentiment
from app.models import Article, Search, SearchSource
from app.models.source import Source, SourceType
from app.schemas.search_request import SearchRequest
from app.schemas.search_response import (
    SearchResponse,
    SearchResultItem,
    SentimentScores,
)
from app.utils.boolean_utils import apply_boolean_filters
from app.utils.metadata_utils import (
    get_all_sources,
    get_source_name_map,
    get_sources_by_names,
)
from app.workers.core.query import Query as ScraperQuery
from app.workers.core.utils import load_proxies
from app.workers.scrapers.gov_scraper import GovScraper
from app.workers.scrapers.news_scraper import NewsScraper
from app.workers.scrapers.social_scraper import SocialScraper


class SearchService:
    def __init__(self) -> None:
        self.scraper_mapping: Dict[SourceType, Type[Any]] = {
            SourceType.NEWS: NewsScraper,
            SourceType.SOCIAL: SocialScraper,
            SourceType.OFFICIAL: GovScraper,
        }
        self.cleaner = DataCleaner()
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.tsa_model = NewsSentiment()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=False
    )
    async def _safe_scrape(
            self, scraper_inst: Any, query_text: str, sources: List[Source]
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Runs scraper with exponential backoff.
        Now includes 'sources' to match the scraper's .run() signature.
        """
        worker_query = ScraperQuery(text=query_text)
        # Passing all 4 required arguments to the scraper
        return await scraper_inst.run(worker_query, "en-US", "US", sources)

    async def execute_search(self, request: SearchRequest) -> SearchResponse:
        """
        Primary entry point for searches. 
        If search_id is provided, it filters existing data. 
        Otherwise, it triggers a new scraping pipeline.
        """
        start_time = time.time()
        
        # Identity Resolution (UUID)
        search_id: Optional[UUID] = request.search_id

        # Ingestion Path (New Scrape)
        if not search_id:
            search_id = await self._ingest_new_search(request)

        # Retrieval & Boolean Filtering Path
        results = self._fetch_filtered_articles(search_id, request)

        execution_time = (time.time() - start_time) * 1000

        # Ensure we return the ID as a UUID object
        return SearchResponse(
            search_id=search_id,
            total_count=len(results),
            execution_time_ms=round(execution_time, 2),
            results=results
        )

    async def _ingest_new_search(self, request: SearchRequest) -> UUID:
        """Performs full scraping, cleaning, and persistence for a new query."""
        requested_sources = get_sources_by_names(request.platforms)
        if not requested_sources:
            all_enabled = get_all_sources(only_enabled=True)
            requested_sources = [
                s for s in all_enabled 
                if any(p.lower() in s.name.lower() for p in request.platforms)
            ]

        all_sources = get_all_sources(only_enabled=True)
        requested_ids = set(s.id for s in requested_sources)
        all_ids = set(s.id for s in all_sources)
        is_full_search = requested_ids == all_ids

        with Session(engine) as session:
            db_search = Search(
                query_text=request.query,
                request_limit=request.limit,
                all_sources_requested=is_full_search,
            )
            session.add(db_search)
            session.flush() # SQLModel handles UUID generation if set to primary_key

            if not is_full_search:
                for source in requested_sources:
                    if source.id:
                        session.add(
                            SearchSource(
                                search_id=db_search.id,
                                source_id=source.id
                            )
                        )

            proxies = load_proxies(source="db")
            sources_by_type: Dict[SourceType, List[Source]] = {}
            for src in requested_sources:
                sources_by_type.setdefault(src.source_type, []).append(src)

            tasks = []
            task_metadata = []

            for s_type, sources in sources_by_type.items():
                scraper_cls = self.scraper_mapping.get(s_type)
                if scraper_cls:
                    ua = (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/122.0.0.0 Safari/537.36"
                    )

                    scraper_inst = scraper_cls(proxies=proxies, user_agent=ua)
                    tasks.append(self._safe_scrape(scraper_inst,
                                                   request.query, sources))
                    task_metadata.append(s_type)

            scraper_results = await asyncio.gather(*tasks, return_exceptions=True)

            temp_items = []
            for s_type, platform_output in zip(task_metadata, scraper_results):
                if (
                    isinstance(platform_output, (BaseException, Exception))
                    or platform_output is None
                ):
                    continue

                for item in platform_output:
                    if not item or not isinstance(item, dict):
                        continue
                    raw_text = item.get("content", "") or item.get("title", "")
                    if not self.cleaner.is_english(raw_text):
                        continue

                    source_id = int(item.get("source_id", 0))
                    name_map = get_source_name_map()
                    source_name = name_map.get(source_id, "")

                    print(f"This is the raw text from the source {source_name}")
                    print(raw_text)
                    #if "Reddit" in source_name:
                    #    raw_text = self.cleaner.clean_reddit_content(raw_text)

                    item["content"] = self.cleaner.clean(raw_text)
                    temp_items.append(item)
                    print("Text after cleaning")
                    print(item["content"])

            if temp_items:
                query_emb = self.model.encode(request.query, convert_to_tensor=True)
                corpus_texts = [
                    f"{i['title']} {i['content'][:200]}" for i in temp_items
                ]
                corpus_embs = self.model.encode(corpus_texts, convert_to_tensor=True)
                cosine_scores = util.cos_sim(query_emb, corpus_embs)[0]

                for idx, item in enumerate(temp_items):
                    score = float(cosine_scores[idx])
                    source_id = int(item.get("source_id", 0))
                    # Sentiment analysis
                    doc_sentiment:Tuple[str, float] = self.tsa_model.make_inference(
                        text=item["content"])
                    db_article = Article(
                        title=item.get("title", ""),
                        content=item.get("content", ""),
                        url=item.get("url", ""),
                        published_at=item.get("published_at"),
                        search_id=db_search.id,
                        source_id=source_id,
                        relevance_score=score,
                        sentiment_score = doc_sentiment[1],
                        sentiment_label = doc_sentiment[0],
                    )
                    session.add(db_article)
                session.commit()
            
            # The id is now a UUID object
            return db_search.id

    def _fetch_filtered_articles(
        self, search_id: UUID, request: SearchRequest
    ) -> List[SearchResultItem]:
        """Fetches articles for a search_id (UUID) and applies filters."""
        with Session(engine) as session:
            statement = select(Article).where(Article.search_id == search_id)
            
            if request.filters:
                statement = apply_boolean_filters(statement, request.filters)
            
            statement = statement.order_by(desc(Article.relevance_score))
            limit = request.limit if request.limit > 0 else 20
            statement = statement.limit(limit)
            
            db_articles = session.exec(statement).all()
            
            return [
                self._map_article_to_search_result_item(art)
                for art in db_articles
            ]

    def _map_article_to_search_result_item(self, art:Article) -> SearchResultItem:
        content = art.content or ""
        if len(content) > 300:
            content = content[:297] + "..."

        raw_date = art.published_at
        if not raw_date:
            parsed_date = datetime.now(timezone.utc)
        elif isinstance(raw_date, datetime):
            parsed_date = raw_date
        else:
            try:
                parsed_date = parser.parse(str(raw_date))
                if parsed_date.tzinfo is None:
                    parsed_date = parsed_date.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                parsed_date = datetime.now(timezone.utc)

        # Resolve Source Name from Utility mapping
        name_map = get_source_name_map()
        source_id = art.source_id
        source_name = name_map.get(
            int(source_id) if source_id is not None else 0, "Web"
        )
        #Resolve Sentiment Analysis mapping
        sentiment_obj: SentimentScores = SentimentScores(
            label = art.sentiment_label or "",
            score = art.sentiment_score or None,
        )

        return SearchResultItem(
            id=hashlib.md5((art.url or "").encode()).hexdigest(),
            source=source_name,
            title=art.title,
            content=content or art.title,
            url=art.url or "",
            published_at=parsed_date,
            sentiment=sentiment_obj,
            relevance_score=art.relevance_score,
        )

# Create a singleton instance to be used by the routes
search_service = SearchService()