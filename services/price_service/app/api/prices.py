# services/price_service/app/api/prices.py
from datetime import datetime
try:
    from datetime import UTC
except ImportError:
    from datetime import timezone as UTC
from fastapi import APIRouter, HTTPException, status, Depends
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List

from app.models.schemas import PriceEntry
from app.core.mongodb import get_database
from app.core.logging import logger

router = APIRouter()

@router.post("", response_model=PriceEntry)
async def create_price_entry(
    price_entry: PriceEntry,
    db: AsyncIOMotorClient = Depends(get_database)
):
    try:
        result = await db.prices.insert_one(price_entry.model_dump())
        created_entry = await db.prices.find_one({"_id": result.inserted_id})
        return PriceEntry(**created_entry)
    except Exception as e:
        logger.error(f"Failed to create price entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create price entry",
        )

@router.get("/compare/{product_id}")
async def compare_prices(
    product_id: str,
    db: AsyncIOMotorClient = Depends(get_database)
):
    try:
        pipeline = [
            {"$match": {"product_id": product_id}},
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$store_id",
                "latest_price": {"$first": "$price"},
                "latest_timestamp": {"$first": "$timestamp"}
            }},
        ]
        
        prices = await db.prices.aggregate(pipeline).to_list(None)
        return {
            "product_id": product_id,
            "price_comparison": prices
        }
    except Exception as e:
        logger.error(f"Failed to compare prices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare prices",
        )

@router.get("/history/{product_id}")
async def get_price_history(
    product_id: str,
    store_id: str = None,
    db: AsyncIOMotorClient = Depends(get_database)
):
    try:
        match_query = {"product_id": product_id}
        if store_id:
            match_query["store_id"] = store_id
            
        pipeline = [
            {"$match": match_query},
            {"$sort": {"timestamp": -1}},
            {"$limit": 100}  # Limit to last 100 prices
        ]
        
        history = await db.prices.aggregate(pipeline).to_list(None)
        return {
            "product_id": product_id,
            "store_id": store_id,
            "price_history": history
        }
    except Exception as e:
        logger.error(f"Failed to get price history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve price history",
        )