from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Enum, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.article import Article
    from app.models.proxy import ProxyLog
    from app.models.search import Search, SearchSource


# enums for source_type and extraction_method

class SourceType(str, Enum):
    """Categories of platforms we scrape."""
    SOCIAL = "SOCIAL"
    NEWS = "NEWS"
    OFFICIAL = "OFFICIAL"

class ExtractionMethod(str, Enum):
    """Strategy used to collect data."""
    RSS = "RSS"
    STATIC_HTML = "STATIC_HTML"
    INFINITE_SCROLL = "INFINITE_SCROLL"


class Source(SQLModel, table=True):
    """Holds all targeted platforms."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    source_type: SourceType = Field(default=SourceType.NEWS)
    extraction_method: ExtractionMethod = Field(default=ExtractionMethod.RSS)
    base_url: str
    is_enabled: bool = Field(default=True)

    # Relationships
    articles: List["Article"] = Relationship(back_populates="source")
    searches: List["Search"] = Relationship(
        back_populates="sources", link_model="SearchSource"
    )
    proxy_logs: List["ProxyLog"] = Relationship(back_populates="source")
