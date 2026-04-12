from typing import Any

from sqlmodel import col, not_, or_

from app.models.article import Article
from app.schemas.search_request import KeywordFilters


def apply_boolean_filters(statement: Any, filters: KeywordFilters) -> Any:
    """
    Applies boolean keyword filtering to a SQLModel statement.
    Filters are applied case-insensitively across Article.title and Article.content.
    """
    
    # 1. "All of these" (AND logic)
    # Every word must be found in either the title OR the content.
    for word in filters.all_of:
        clean_word = word.strip()
        if clean_word:
            statement = statement.where(
                or_(
                    col(Article.title).ilike(f"%{clean_word}%"),
                    col(Article.content).ilike(f"%{clean_word}%")
                )
            )

    # 2. "At least one" (OR logic)
    # At least one of these words must be in the title or content.
    if filters.any_of:
        any_clauses = []
        for word in filters.any_of:
            clean_word = word.strip()
            if clean_word:
                any_clauses.append(col(Article.title).ilike(f"%{clean_word}%"))
                any_clauses.append(col(Article.content).ilike(f"%{clean_word}%"))
        
        if any_clauses:
            statement = statement.where(or_(*any_clauses))

    # 3. "None of these" (NOT logic)
    # None of these words can be in the title OR the content.
    for word in filters.none_of:
        clean_word = word.strip()
        if clean_word:
            statement = statement.where(
                not_(
                    or_(
                        col(Article.title).ilike(f"%{clean_word}%"),
                        col(Article.content).ilike(f"%{clean_word}%")
                    )
                )
            )

    return statement