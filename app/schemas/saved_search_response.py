from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class SavedSearchResponseItem(BaseModel):
    """Represents a single entry in the user's saved list."""
    id: UUID  # ID of the SavedSearch record
    search_id: UUID
    custom_name: Optional[str]
    query_text: str
    created_at: datetime

class SavedSearchListResponse(BaseModel):
    """The wrapper for the GET /saved-searches endpoint."""
    total: int
    items: List[SavedSearchResponseItem]