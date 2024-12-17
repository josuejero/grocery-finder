# app/routers/users.py
from fastapi import APIRouter, HTTPException, Header, status
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.services.user_service import UserService
from app.services.gateway_service import GatewayService

router = APIRouter()
gateway_service = GatewayService()


@router.get("/me")
async def get_user_profile(authorization: str = Header(None)):
    """
    Retrieve user profile
    """
    if not authorization:
        logger.error("Authorization header missing")
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    return await gateway_service.forward_request(
        method="GET", 
        endpoint="/users/me", 
        headers={"Authorization": authorization}
    )

@router.post("/sync")
async def sync_user(
    username: str,
    authorization: str = Header(...)
):
    """
    Synchronize user data
    """
    return await gateway_service.forward_request(
        method="POST", 
        endpoint=f"/users/sync", 
        headers={"Authorization": authorization},
        params={"username": username}
    )

@router.get("/me/shopping-lists")
async def get_shopping_lists(authorization: str = Header(...)):
    """
    Retrieve user's shopping lists
    """
    return await gateway_service.forward_request(
        method="GET", 
        endpoint="/users/me/shopping-lists", 
        headers={"Authorization": authorization}
    )

@router.post("/me/shopping-lists")
async def create_shopping_list(
    shopping_list: dict,
    authorization: str = Header(...)
):
    """
    Create a new shopping list
    """
    return await gateway_service.forward_request(
        method="POST", 
        endpoint="/users/me/shopping-lists", 
        headers={"Authorization": authorization},
        json=shopping_list
    )

@router.get("/me/shopping-lists/{list_id}")
async def get_shopping_list(
    list_id: int,
    authorization: str = Header(...)
):
    """
    Retrieve a specific shopping list
    """
    return await gateway_service.forward_request(
        method="GET", 
        endpoint=f"/users/me/shopping-lists/{list_id}", 
        headers={"Authorization": authorization}
    )

@router.put("/me/shopping-lists/{list_id}")
async def update_shopping_list(
    list_id: int,
    shopping_list: dict,
    authorization: str = Header(...)
):
    """
    Update a specific shopping list
    """
    try:
        return await gateway_service.forward_request(
            method="PUT", 
            endpoint=f"/users/me/shopping-lists/{list_id}", 
            headers={"Authorization": authorization},
            json=shopping_list
        )
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shopping list not found"
            )
        raise

@router.delete("/me/shopping-lists/{list_id}")
async def delete_shopping_list(
    list_id: int,
    authorization: str = Header(...)
):
    """
    Delete a specific shopping list
    """
    try:
        return await gateway_service.forward_request(
            method="DELETE", 
            endpoint=f"/users/me/shopping-lists/{list_id}", 
            headers={"Authorization": authorization}
        )
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shopping list not found"
            )
        raise