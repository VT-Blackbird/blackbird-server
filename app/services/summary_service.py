import time
from typing import Sequence

from sqlmodel import Session, col, desc, select

from app.db.session import engine
from app.models import Article, Search
from app.schemas.summary_request import SummaryRequest
from app.schemas.summary_response import (
    SummaryQueryResponse,
    SummaryResponse,
    SummaryResponseItem,
)
from app.utils.metadata_utils import get_source_name_map


class SummaryService:
    def __init__(self) -> None:
        pass

    async def execute_summary(self, request: SummaryRequest) -> SummaryResponse:
        start_time = time.time()

        with Session(engine) as session:
            # 1. Find all search IDs associated with this query text
            # We use a join or a subquery to get articles for this specific topic
            # In execute_summary
            statement = (
                select(Article)
                .join(Search)
                .where(Search.query_text == request.query)
                .distinct(col(Article.url))
                # The first order_by MUST be the same as the distinct column
                .order_by(col(Article.url), desc(Article.published_at)
                          )
            )
            db_articles = session.exec(statement).all()

            # 2. Dynamic Source Name Mapping
            name_map = get_source_name_map()

            results = []
            for art in db_articles:
                source_name = name_map.get(art.source_id, "Web")

                item = SummaryResponseItem(
                    id=str(art.id),
                    source=source_name,
                    title=art.title,
                    url=art.url,
                    source_id=str(art.source_id),
                    published_at=art.published_at,
                    sentiment=None,  # Placeholder for ML logic
                    relevance_score=art.relevance_score,
                    geographic_area="US"  # Default or pulled from metadata
                )
                results.append(item)

            execution_time = (time.time() - start_time) * 1000

            return SummaryResponse(
                total_count=len(results),
                execution_time_ms=round(execution_time, 2),
                results=results,
            )

    async def get_queries(self) -> SummaryQueryResponse:
        with Session(engine) as session:
            # 1. Build the query to select the column and apply DISTINCT
            statement = select(Search.query_text).distinct()

            # 2. Execute and get the results as a list of strings
            results_seq: Sequence[str] = session.exec(statement).all()
            results_list = list(results_seq)

            # 3. Return formatted for your Response schema
            return SummaryQueryResponse(queries_list=results_list)

summary_service: SummaryService = SummaryService()