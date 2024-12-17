# services/api_gateway/app/routers/auth.py

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.services.auth_service import AuthService
from app.schemas.auth import Token

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(lambda: AuthService())
):
    return await auth_service.login(form_data.__dict__)

@router.post("/register")
async def register(
    user_data: dict,
    auth_service: AuthService = Depends(lambda: AuthService())
):
    return await auth_service.register(user_data)