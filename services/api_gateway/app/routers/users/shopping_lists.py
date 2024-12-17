# app/routers/users/shopping_lists.py
from fastapi import APIRouter, Depends, Header
from app.services.user_service import UserService

router = APIRouter()

@router.get("")
async def get_shopping_lists(
    authorization: str = Header(...),
    user_service: UserService = Depends(lambda: UserService())
):
    return await user_service.get_shopping_lists(authorization)

@router.post("")
async def create_shopping_list(
    shopping_list: dict,
    authorization: str = Header(...),
    user_service: UserService = Depends(lambda: UserService())
):
    return await user_service.create_shopping_list(authorization, shopping_list)