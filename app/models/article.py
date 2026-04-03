import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, Text, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.search import Search
    from app.models.source import Source


class Article(SQLModel, table=True):
    """The individual data points collected by scrapers."""

    __table_args__ = (
        UniqueConstraint("url", "search_id", name="unique_article_per_search"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str
    # Using Text for potentially long content fields to avoid length limits
    content: str = Field(sa_column=Column(Text))
    url: str = Field(index=True)
    published_at: Optional[datetime] = Field(default=None)

    # Analytics
    sentiment_label: Optional[str] = Field(default=None)
    sentiment_score: Optional[float] = Field(default=None)
    relevance_score: Optional[float] = Field(default=None)

    # Foreign Keys
    search_id: uuid.UUID = Field(foreign_key="search.id", ondelete="CASCADE")
    source_id: int = Field(foreign_key="source.id", ondelete="RESTRICT")

    # Relationships
    search: "Search" = Relationship(back_populates="articles")
    source: "Source" = Relationship(back_populates="articles")
