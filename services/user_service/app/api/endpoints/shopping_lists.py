from datetime import datetime, UTC
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.db.database import get_db
from app.db.models import UserModel, ShoppingListModel
from app.schemas.shopping_list import (
    ShoppingList,
    ShoppingListCreate,
    ShoppingListUpdate
)
from app.api.dependencies import get_current_user

router = APIRouter(tags=["shopping_lists"])

@router.post("/users/me/shopping-lists", response_model=ShoppingList)
async def create_shopping_list(
    shopping_list: ShoppingListCreate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        logger.debug(f"Creating shopping list with data: {shopping_list.model_dump()}")
        new_list = ShoppingListModel(
            user_id=current_user.id,
            name=shopping_list.name,
            items=shopping_list.model_dump()["items"]
        )
        
        db.add(new_list)
        db.commit()
        db.refresh(new_list)
        logger.debug(f"Created shopping list with ID: {new_list.id}")
        
        return new_list
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create shopping list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/users/me/shopping-lists")
async def get_shopping_lists(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        logger.debug(f"Fetching shopping lists for user: {current_user.username}")
        lists = db.query(ShoppingListModel).filter(
            ShoppingListModel.user_id == current_user.id,
            ShoppingListModel.is_active == True
        ).all()
        logger.debug(f"Found {len(lists)} shopping lists")
        return lists
    except Exception as e:
        logger.error(f"Failed to get shopping lists: {e}")
        logger.exception("Traceback:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
@router.get("/users/me/shopping-lists/{list_id}", response_model=ShoppingList)
async def get_shopping_list(
    list_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    shopping_list = db.query(ShoppingListModel).filter(
        ShoppingListModel.id == list_id,
        ShoppingListModel.user_id == current_user.id,
        ShoppingListModel.is_active == True
    ).first()
    
    if not shopping_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping list not found"
        )
    
    return shopping_list

@router.put("/users/me/shopping-lists/{list_id}", response_model=ShoppingList)
async def update_shopping_list(
    list_id: int,
    shopping_list_update: ShoppingListUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        shopping_list = db.query(ShoppingListModel).filter(
            ShoppingListModel.id == list_id,
            ShoppingListModel.user_id == current_user.id,
            ShoppingListModel.is_active == True
        ).first()
        
        if not shopping_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shopping list not found"
            )
        
        update_data = shopping_list_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(shopping_list, field, value)
        
        shopping_list.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(shopping_list)
        
        return shopping_list
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update shopping list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/users/me/shopping-lists/{list_id}")
async def delete_shopping_list(
    list_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        shopping_list = db.query(ShoppingListModel).filter(
            ShoppingListModel.id == list_id,
            ShoppingListModel.user_id == current_user.id,
            ShoppingListModel.is_active == True
        ).first()
        
        if not shopping_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shopping list not found"
            )
        
        shopping_list.is_active = False
        shopping_list.updated_at = datetime.now(UTC)
        db.commit()
        
        return {
            "status": "success",
            "message": "Shopping list deleted"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete shopping list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )