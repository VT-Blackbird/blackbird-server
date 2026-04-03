from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.search_response import SentimentScores, SearchResultItem, SearchMetrics

#Information per article
class SummaryResponseItem(BaseModel):
    id: str
    source: str = Field(..., json_schema_extra={"example": "Reddit"})
    title: Optional[str] = None
    url: str
    source_id: Optional[str] = None
    published_at: datetime
    sentiment: Optional[SentimentScores] = None
    relevance_score: float | None = None
    geographic_area: str | None = None

#Returns a list of Summary Response Items
class SummaryResponse(BaseModel):
    """
    The final 'Package' sent back to the frontend of summary responses.
    """

    total_count: int
    execution_time_ms: float
    results: List[SummaryResponseItem]

class SummaryQueryResponse(BaseModel):
    queries_list: List[str]