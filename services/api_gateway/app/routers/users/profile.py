# app/routers/users/profile.py
from fastapi import APIRouter, Depends, Header
from app.services.user_service import UserService

router = APIRouter()

@router.get("/me")
async def get_user_profile(
    authorization: str = Header(...),
    user_service: UserService = Depends(lambda: UserService())
):
    return await user_service.get_profile(authorization)