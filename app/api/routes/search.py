from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.search_request import SearchRequest
from app.schemas.search_response import SearchResponse
from app.services.search_service import search_service

router = APIRouter()


@router.post("/", response_model=SearchResponse)
async def perform_search(
    request: SearchRequest, current_user: User = Depends(get_current_user)
) -> SearchResponse:
    # If request is invalid, FastAPI returns 422 before even getting here.
    try:
        return await search_service.execute_search(request)
    except ValueError as e:
        # Catch specific business logic errors (like an unsupported platform)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Reserve 500 for actual server crashes
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.delete("/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_search(
    search_id: UUID,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Permanently deletes a search and all its associated results.
    """
    success = search_service.delete_search(db=db, search_id=search_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search record not found or you do not have permission to delete it."
        )

    return None
