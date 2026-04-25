from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.db.session import get_db
from app.models.user import User  # Assuming your user model location
from app.api.deps import get_current_user
from app.schemas.saved_search import (
    SavedSearchRequest,
    SavedSearchResponseItem,
    SavedSearchListResponse
)
from app.services.saved_search_service import saved_search_service

router = APIRouter()

@router.post("/", response_model=SavedSearchResponseItem, status_code=status.HTTP_201_CREATED)
async def create_saved_search(
        request: SavedSearchRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Creates a new bookmark for a search.
    """
    # Logic to check if the search_id actually exists in the Search table
    # usually handled within the service layer
    saved_item = saved_search_service.save(
        db=db,
        user_id=current_user.id,
        search_id=request.search_id,
        custom_name=request.custom_name
    )
    return saved_item


@router.get("/", response_model=SavedSearchListResponse)
async def get_saved_searches(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Retrieves all saved searches for the logged-in user.
    """
    items = saved_search_service.get_all_for_user(db=db, user_id=current_user.id)

    return SavedSearchListResponse(
        total=len(items),
        items=items
    )


@router.delete("/{saved_search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_search(
        saved_search_id: UUID,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Deletes a specific saved search bookmark.
    """
    success = saved_search_service.delete(
        db=db,
        user_id=current_user.id,
        saved_search_id=saved_search_id
    )

    if not success:
        # Raise a 404 if the ID doesn't exist OR doesn't belong to the user
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved search not found or you do not have permission to delete it."
        )

    # 204 No Content doesn't return a body
    return None