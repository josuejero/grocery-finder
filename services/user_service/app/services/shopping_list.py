from datetime import datetime, UTC
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.db.models import ShoppingListModel, UserModel
from app.schemas.shopping_list import ShoppingListCreate, ShoppingListUpdate

async def create_shopping_list(
    db: Session,
    user: UserModel,
    shopping_list: ShoppingListCreate
) -> ShoppingListModel:
    try:
        new_list = ShoppingListModel(
            user_id=user.id,
            name=shopping_list.name,
            items=shopping_list.items
        )
        db.add(new_list)
        db.commit()
        db.refresh(new_list)
        return new_list
    except Exception as e:
        logger.error(f"Failed to create shopping list: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create shopping list"
        )

async def get_user_shopping_lists(
    db: Session,
    user: UserModel,
    skip: int = 0,
    limit: int = 100
) -> List[ShoppingListModel]:
    try:
        return db.query(ShoppingListModel).filter(
            and_(
                ShoppingListModel.user_id == user.id,
                ShoppingListModel.is_active == True
            )
        ).offset(skip).limit(limit).all()
    except Exception as e:
        logger.error(f"Failed to get shopping lists: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve shopping lists"
        )

async def get_shopping_list(
    db: Session,
    user: UserModel,
    list_id: int
) -> ShoppingListModel:
    shopping_list = db.query(ShoppingListModel).filter(
        and_(
            ShoppingListModel.id == list_id,
            ShoppingListModel.user_id == user.id,
            ShoppingListModel.is_active == True
        )
    ).first()
    
    if not shopping_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping list not found"
        )
    
    return shopping_list

async def update_shopping_list(
    db: Session,
    user: UserModel,
    list_id: int,
    shopping_list_update: ShoppingListUpdate
) -> ShoppingListModel:
    shopping_list = await get_shopping_list(db, user, list_id)
    
    try:
        update_data = shopping_list_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(shopping_list, field, value)
        
        shopping_list.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(shopping_list)
        return shopping_list
    except Exception as e:
        logger.error(f"Failed to update shopping list: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update shopping list"
        )

async def delete_shopping_list(
    db: Session,
    user: UserModel,
    list_id: int
) -> bool:
    shopping_list = await get_shopping_list(db, user, list_id)
    
    try:
        shopping_list.is_active = False
        shopping_list.updated_at = datetime.now(UTC)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to delete shopping list: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete shopping list"
        )

async def get_shopping_list_items(
    db: Session,
    user: UserModel,
    list_id: int
) -> List[dict]:
    shopping_list = await get_shopping_list(db, user, list_id)
    return shopping_list.items

async def update_shopping_list_items(
    db: Session,
    user: UserModel,
    list_id: int,
    items: List[dict]
) -> ShoppingListModel:
    shopping_list = await get_shopping_list(db, user, list_id)
    
    try:
        shopping_list.items = items
        shopping_list.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(shopping_list)
        return shopping_list
    except Exception as e:
        logger.error(f"Failed to update shopping list items: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update shopping list items"
        )