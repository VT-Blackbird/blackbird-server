import uuid
from typing import List, Optional

from sqlalchemy.orm import joinedload
from sqlmodel import Session, select

from app.models.saved_search import SavedSearch
from app.models.search import Search
from app.schemas.saved_search_response import SavedSearchResponseItem


class SavedSearchService:
    def save(
            self, db: Session, user_id: uuid.UUID, search_id: uuid.UUID,
            custom_name: Optional[str] = None
    ) -> SavedSearchResponseItem | None:
        # 1. Verification: Ensure the search actually exists
        db_search = db.get(Search, search_id)
        if not db_search:
            return None  # The router will handle this as a 404

        # 2. Check for existing bookmark to prevent duplicates
        existing = db.exec(
            select(SavedSearch).where(
                SavedSearch.user_id == user_id,
                SavedSearch.search_id == search_id
            )
        ).first()

        if existing:
            return self._map_to_response(existing)

        # 3. Create and persist
        new_save = SavedSearch(
            user_id=user_id,
            search_id=search_id,
            custom_name=custom_name
        )
        db.add(new_save)
        db.commit()
        db.refresh(new_save)

        return self._map_to_response(new_save)

    def get_all_for_user(self, db: Session,
                         user_id: uuid.UUID) -> List[SavedSearchResponseItem]:
        # We use joinedload to fetch the Search data in the same query (Eager Loading)
        statement = (
            select(SavedSearch)
            .where(SavedSearch.user_id == user_id)
            .options(joinedload(SavedSearch.search))
            .order_by(SavedSearch.id)  # Or order by a timestamp if you kept one
        )
        results = db.exec(statement).all()

        return [self._map_to_response(item) for item in results]

    def delete(self, db: Session, user_id: uuid.UUID,
               saved_search_id: uuid.UUID) -> bool:
        statement = select(SavedSearch).where(
            SavedSearch.id == saved_search_id,
            SavedSearch.user_id == user_id
        )
        result = db.exec(statement).first()

        if not result:
            return False

        db.delete(result)
        db.commit()
        return True

    def _map_to_response(self, item: SavedSearch) -> SavedSearchResponseItem:
        """
        Helper to transform the DB model + Relationship into the Response Schema.
        """

        return SavedSearchResponseItem(
            id=item.id,
            search_id=item.search_id,
            custom_name=item.custom_name,
            query_text=item.search.query_text,
            created_at=item.search.created_at,
        )

# Singleton instance
saved_search_service = SavedSearchService()