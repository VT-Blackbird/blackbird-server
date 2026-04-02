from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.source import Source


class Proxy(SQLModel, table=True):
    """Proxy server configuration for rotation and resilience."""

    id: Optional[int] = Field(default=None, primary_key=True)
    server: str = Field(index=True)
    username: Optional[str] = None
    password: Optional[str] = None
    region: str
    language: str
    is_active: bool = Field(default=True)
    last_used_at: Optional[datetime] = Field(default=None)

    # Relationships
    logs: List["ProxyLog"] = Relationship(back_populates="proxy")


class ProxyLog(SQLModel, table=True):
    """Historical log of proxy performance against specific sources."""

    __tablename__ = "proxy_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status_code: int

    proxy_id: int = Field(foreign_key="proxy.id", ondelete="CASCADE")
    source_id: int = Field(foreign_key="source.id", ondelete="CASCADE")

    # Relationships
    proxy: Proxy = Relationship(back_populates="logs")
    source: "Source" = Relationship(back_populates="proxy_logs")
