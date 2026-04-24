from typing import Dict, List, Optional

from sqlmodel import Session, select

from app.db.session import engine
from app.models.source import Source


def get_all_sources(only_enabled: bool = True) -> List[Source]:
    """
    Fetches all Source records from the database.
    """
    with Session(engine) as session:
        statement = select(Source)
        if only_enabled:
            statement = statement.where(Source.is_enabled)
        return session.exec(statement).all()

def get_enabled_source_names() -> List[str]:
    """
    Returns a list of names for all enabled sources.
    Used for dynamic defaults in API schemas.
    """
    return [s.name for s in get_all_sources(only_enabled=True)]

def get_source_id_map() -> Dict[str, int]:
    """
    Returns a mapping of Source Name -> Source ID.
    Example: {"Reddit": 1, "Google News": 2, ...}
    """
    sources = get_all_sources(only_enabled=False)
    return {s.name: s.id for s in sources if s.id is not None}

def get_source_name_map() -> Dict[int, str]:
    """
    Returns a mapping of Source ID -> Source Name.
    Example: {1: "Reddit", 2: "Google News", ...}
    """
    sources = get_all_sources(only_enabled=False)
    return {s.id: s.name for s in sources if s.id is not None}

def get_sources_by_names(names: List[str]) -> List[Source]:
    """
    Fetches specific Source objects by their names.
    """
    if not names:
        return []
    
    with Session(engine) as session:
        statement = select(Source).where(Source.name.in_(names))
        return session.exec(statement).all()

def get_source_by_id(source_id: int) -> Optional[Source]:
    """
    Fetches a single Source record by its primary key.
    """
    with Session(engine) as session:
        return session.get(Source, source_id)