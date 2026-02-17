from pydantic import BaseModel, Field
from typing import Optional, List


class SearchRequest(BaseModel):
    """
    Request schema for search queries coming from the frontend.
    """

    query: str = Field(
        ...,
        min_length=1,
        description="User search query string"
    )

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of results to return"
    )