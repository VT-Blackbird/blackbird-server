
from fastapi import APIRouter, HTTPException, Depends
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.summary_request import SummaryRequest
from app.schemas.summary_response import SummaryQueryResponse, SummaryResponse
from app.services.summary_service import summary_service

router = APIRouter()

@router.post("/", response_model=SummaryResponse)
async def perform_summary(request: SummaryRequest,
                          current_user: User =
                          Depends(get_current_user))-> SummaryResponse:
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
async def get_queries(current_user: User = Depends(get_current_user)
                      )-> SummaryQueryResponse:
    try:
        return await summary_service.get_queries()
    except ValueError as e:
        # Business Logic Errors
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Reserve 500 for actual server crashes
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")