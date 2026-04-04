from typing import List

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """
    Request schema for search queries coming from the frontend.
    """

    query: str = Field(..., min_length=1, description="User search query string")

    limit: int = Field(
        default=20, ge=1, le=100, description="Maximum number of results to return"
    )

    platforms: List[str] = Field(
        default=["Reddit", "Gov", "News"], description="Which sites to scrape"
    )
