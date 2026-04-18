from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# Define the "Small" parts first so the "Big" parts can use them
class SentimentScores(BaseModel):
    label: str = Field(..., description="Positive, Negative, or Neutral")
    score: float = Field(..., description="Intensity score, e.g., 0.95")


class SearchMetrics(BaseModel):
    avg_sentiment: float
    sentiment_distribution: Dict[str, int]  # e.g., {"Positive": 10, "Neutral": 5}
    top_keywords: List[str]


class SearchResultItem(BaseModel):
    id: str
    source: str = Field(..., json_schema_extra={"example": "Reddit"})
    title: Optional[str] = None
    content: str
    url: str
    published_at: datetime
    sentiment: Optional[SentimentScores] = None
    relevance_score: float | None = None


class SearchResponse(BaseModel):
    """
    The final 'Package' sent back to the frontend.
    """
    
    search_id: UUID = Field(
        ..., description="The unique ID of this search session for future filtering"
    )
    total_count: int
    execution_time_ms: float
    metrics: Optional[SearchMetrics] = None
    results: List[SearchResultItem]