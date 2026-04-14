from typing import List, Optional

from pydantic import BaseModel, Field

from app.utils.metadata_utils import get_enabled_source_names


class KeywordFilters(BaseModel):
    """
    Boolean filtering logic for post-scrape refinement.
    Maps to the "All of these", "At least one", and "None of these" UI boxes.
    """
    all_of: List[str] = Field(
        default_factory=list,
        description="Must contain ALL these words"
    )
    any_of: List[str] = Field(
        default_factory=list,
        description="Must contain at least ONE of these"
    )
    none_of: List[str] = Field(
        default_factory=list,
        description="Must NOT contain any of these"
    )

class SearchRequest(BaseModel):
    """
    Request schema for search queries coming from the frontend.
    Supports both new scrapes and filtering existing search sessions via search_id.
    """
    query: str = Field(..., min_length=1, description="User search query string")

    limit: int = Field(
        default=20, ge=1, le=100, description="Maximum number of results to return"
    )

    platforms: List[str] = Field(
        default_factory=get_enabled_source_names,
        description="List of platform names to scrape. Defaults to all enabled sources."
    )

    # Boolean Search & Identity Logic
    search_id: Optional[int] = Field(
        None, 
        description=(
            "Target a specific existing search session by its ID to skip "
            "scraping and apply filters"
        )
    )
    
    filters: Optional[KeywordFilters] = Field(
        None, 
        description="Post-scrape boolean filters for content refinement"
    )