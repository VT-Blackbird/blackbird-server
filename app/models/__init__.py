# Import all models to ensure they are registered with SQLModel.metadata
from .article import Article
from .proxy import Proxy, ProxyLog
from .search import Search, SearchSource
from .source import ExtractionMethod, Source, SourceType  # Added Enums here
from .saved_search import SavedSearch
from .user import User
# This allows other parts of the app to do: from app.models import SourceType
__all__ = [
    "Search",
    "SearchSource",
    "Source",
    "SourceType",
    "ExtractionMethod",
    "Article",
    "Proxy",
    "ProxyLog",
    "SavedSearch",
    "User",
]
