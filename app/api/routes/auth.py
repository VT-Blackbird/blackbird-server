from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from app.services.auth_service import auth_service

router = APIRouter()

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    access_token = auth_service.authenticate_user(
        username=form_data.username,
        password=form_data.password
    )
    return {"access_token": access_token, "token_type": "bearer"}