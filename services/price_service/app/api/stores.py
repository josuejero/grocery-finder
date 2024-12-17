# services/price_service/app/api/stores.py
from fastapi import APIRouter, HTTPException, status, Depends
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List

from app.models.schemas import Store
from app.core.mongodb import get_database
from app.core.logging import logger

router = APIRouter()

@router.post("", response_model=Store)
async def create_store(
    store: Store,
    db: AsyncIOMotorClient = Depends(get_database)
):
    try:
        result = await db.stores.insert_one(store.model_dump())
        created_store = await db.stores.find_one({"_id": result.inserted_id})
        return Store(**created_store)
    except Exception as e:
        logger.error(f"Failed to create store: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create store",
        )

@router.get("", response_model=List[Store])
async def list_stores(
    active_only: bool = True,
    db: AsyncIOMotorClient = Depends(get_database)
):
    try:
        query = {"active": True} if active_only else {}
        cursor = db.stores.find(query)
        stores = await cursor.to_list(None)
        return [Store(**store) for store in stores]
    except Exception as e:
        logger.error(f"Failed to list stores: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list stores",
        )

@router.get("/{store_id}", response_model=Store)
async def get_store(
    store_id: str,
    db: AsyncIOMotorClient = Depends(get_database)
):
    try:
        store = await db.stores.find_one({"id": store_id})
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Store not found"
            )
        return Store(**store)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get store: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve store",
        )

@router.put("/{store_id}", response_model=Store)
async def update_store(
    store_id: str,
    store_update: Store,
    db: AsyncIOMotorClient = Depends(get_database)
):
    try:
        store = await db.stores.find_one({"id": store_id})
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Store not found"
            )
            
        update_data = store_update.model_dump(exclude_unset=True)
        result = await db.stores.update_one(
            {"id": store_id},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Store update failed"
            )
            
        updated_store = await db.stores.find_one({"id": store_id})
        return Store(**updated_store)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update store: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update store",
        )

@router.delete("/{store_id}")
async def delete_store(
    store_id: str,
    db: AsyncIOMotorClient = Depends(get_database)
):
    try:
        store = await db.stores.find_one({"id": store_id})
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Store not found"
            )
            
        result = await db.stores.update_one(
            {"id": store_id},
            {"$set": {"active": False}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Store deactivation failed"
            )
            
        return {"status": "success", "message": "Store deactivated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete store: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete store",
        )