from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class SavedSearchRequest(BaseModel):
    search_id: UUID
    custom_name: Optional[str] = None