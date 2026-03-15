from fastapi import APIRouter, HTTPException

from app.schemas.search_request import SearchRequest
from app.schemas.search_response import SearchResponse
from app.services.search_service import search_service  # Import the service

router = APIRouter()


@router.post("/", response_model=SearchResponse)
async def perform_search(request: SearchRequest)-> SearchResponse:
    # If request is invalid, FastAPI returns 422 before even getting here.
    try:
        return search_service.execute_search(request)
    except ValueError as e:
        # Catch specific business logic errors (like an unsupported platform)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Reserve 500 for actual server crashes
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
