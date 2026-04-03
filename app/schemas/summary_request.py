from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

class SummaryRequest(BaseModel):
    """
    Request schema for search queries coming from the frontend.
    """
    query: str = Field(..., min_length=1, description="User search query string")
    start_date: datetime = Field(..., description="Start date for query")
    end_date: datetime = Field(..., description="End date for query")
    sources: List[str] = Field(..., description="Sources to search")

