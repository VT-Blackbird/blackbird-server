import time
from datetime import datetime, timezone
from app.schemas.search_request import SearchRequest
from app.schemas.search_response import SearchResponse, SearchResultItem, SearchMetrics, SentimentScores


class SearchService:
    def execute_search(self, request: SearchRequest) -> SearchResponse:
        start_time = time.time()

        # 1. TODO: Call Scrapers (workers/scraper.py)
        # 2. TODO: Call ML models (ml/sentiment.py)

        # For now, we keep the mock logic here
        mock_results = [
            SearchResultItem(
                id="101",
                source="Reddit",
                content=f"Results for {request.query}",
                url="https://reddit.com",
                published_at=datetime.now(timezone.utc),
                sentiment=SentimentScores(label="Neutral", score=0.5)
            )
        ]

        execution_time = (time.time() - start_time) * 1000

        return SearchResponse(
            total_count=len(mock_results),
            execution_time_ms=round(execution_time, 2),
            results=mock_results
        )


# Create a singleton instance to be used by the routes
search_service = SearchService()