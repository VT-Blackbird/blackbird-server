from typing import Any, Coroutine

from fastapi import APIRouter, HTTPException

from app.schemas.summary_request import SummaryRequest
from app.schemas.summary_response import SummaryResponse, SummaryQueryResponse
from app.services.summary_service import summary_service

router = APIRouter()

@router.post("/", response_model=SummaryResponse)
async def perform_summary(request: SummaryRequest)-> SummaryResponse:
    # If request is invalid, FastAPI returns 422 before even getting here.
    try:
        return await summary_service.execute_summary(request)
    except ValueError as e:
        # Catch specific business logic errors (like an unsupported platform)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Reserve 500 for actual server crashes
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

#Add a get request to obtain the unique queries from the database
@router.get("/queries")
async def get_queries()-> SummaryQueryResponse:
    try:
        return await summary_service.get_queries()
    except ValueError as e:
        # Catch specific business logic errors (like an unsupported platform)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Reserve 500 for actual server crashes
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")