import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import CheckConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.article import Article
    from app.models.source import Source


class SearchSource(SQLModel, table=True):
    """Link table for many-to-many relationship between Search and Source."""

    __tablename__ = "search_source"

    search_id: uuid.UUID = Field(
        foreign_key="search.id", primary_key=True, ondelete="CASCADE"
    )
    source_id: int = Field(
        foreign_key="source.id", primary_key=True, ondelete="CASCADE"
    )


class Search(SQLModel, table=True):
    __table_args__ = (
        CheckConstraint(
            "request_limit > 0 AND request_limit <= 500",
            name="check_request_limit_range",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    query_text: str = Field(index=True)
    request_limit: int = Field(default=20, ge=1, le=500)
    all_sources_requested: bool = Field(default=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = Field(default=None)

    # Relationships
    articles: List["Article"] = Relationship(
        back_populates="search",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    sources: List["Source"] = Relationship(
        back_populates="searches", link_model=SearchSource
    )
