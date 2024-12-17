# services/price_service/app/api/products.py
from fastapi import APIRouter, HTTPException, status, Depends
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Optional

from app.models.schemas import Product
from app.core.mongodb import get_database
from app.core.logging import logger

router = APIRouter()

@router.post("", response_model=Product)
async def create_product(
    product: Product,
    db: AsyncIOMotorClient = Depends(get_database)
):
    try:
        result = await db.products.insert_one(product.model_dump())
        created_product = await db.products.find_one({"_id": result.inserted_id})
        return Product(**created_product)
    except Exception as e:
        logger.error(f"Failed to create product: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create product",
        )

@router.get("/search")
async def search_products(
    query: str,
    category: Optional[str] = None,
    limit: int = 10,
    db: AsyncIOMotorClient = Depends(get_database)
):
    try:
        search_query = {
            "name": {"$regex": query, "$options": "i"}
        }
        if category:
            search_query["category"] = category
            
        cursor = db.products.find(search_query).limit(limit)
        products = await cursor.to_list(None)
        return products
    except Exception as e:
        logger.error(f"Failed to search products: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search products",
        )

@router.get("/{product_id}", response_model=Product)
async def get_product(
    product_id: str,
    db: AsyncIOMotorClient = Depends(get_database)
):
    try:
        product = await db.products.find_one({"id": product_id})
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        return Product(**product)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get product: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve product",
        )