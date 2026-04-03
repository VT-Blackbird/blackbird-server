import time
from typing import List
from sqlmodel import Session, select
from app.db.session import engine
from app.models import Search, Article  # Ensure Article is imported
from app.schemas.summary_request import SummaryRequest
from app.schemas.summary_response import (
    SummaryResponse,
    SummaryResponseItem,
    SummaryQueryResponse
)

class SummaryService:
    def __init__(self):
        print("Summary Service")
        pass

    async def execute_summary(self, request: SummaryRequest) -> SummaryResponse:
        start_time = time.time()

        with Session(engine) as session:
            # 1. Find all search IDs associated with this query text
            # We use a join or a subquery to get articles for this specific topic
            statement = (
                select(Article)
                .join(Search)
                .where(Search.query_text == request.query)
                .distinct(Article.url)
                .order_by(Article.published_at.desc())
            )
            db_articles = session.exec(statement).all()

            # 2. Map Database Article objects to SummaryResponseItem schema
            results = []
            for art in db_articles:
                # Map source IDs back to names if necessary
                source_map = {1: "Reddit", 2: "Google News", 3: "USA.gov"}
                source_name = source_map.get(art.source_id, "Web")

                item = SummaryResponseItem(
                    id=str(art.id),
                    source=source_name,
                    title=art.title,
                    url=art.url,
                    source_id=str(art.source_id),
                    published_at=art.published_at,
                    sentiment=None,  # Placeholder for your ML logic
                    relevance_score=None,
                    geographic_area="US"  # Default or pulled from metadata
                )
                results.append(item)

            execution_time = (time.time() - start_time) * 1000

            # 3. Return the fully populated Package
            return SummaryResponse(
                total_count=len(results),
                execution_time_ms=round(execution_time, 2),
                results=results
            )

    async def get_queries(self) -> SummaryQueryResponse:
        with Session(engine) as session:
            # 1. Build the query to select the column and apply DISTINCT
            statement = select(Search.query_text).distinct()

            # 2. Execute and get the results as a list of strings
            results: List[str] = session.exec(statement).all()

            # Based on your table data, 'results' would be:
            # ["US Air Force Iran Latest", "US Air Force Leadership"]
            print(results)
            # 3. Return formatted for your Response schema
            return SummaryQueryResponse(queries_list=results)

summary_service = SummaryService()