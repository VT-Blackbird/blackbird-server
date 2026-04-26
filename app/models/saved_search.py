import uuid
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .search import Search


class SavedSearch(SQLModel, table=True):
    __tablename__ = "saved_search"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # The glue
    search_id: uuid.UUID = Field(foreign_key="search.id", index=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)

    # The only unique data: what the user decided to call it
    custom_name: Optional[str] = Field(default=None)

    # The Python "Shortcut"
    search: "Search" = Relationship()