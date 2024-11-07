import logging
import os
import sys
from datetime import datetime
import datetime as dt
try:
    from datetime import UTC
except ImportError:
    UTC = dt.timezone.utc
from typing import List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Price Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGODB_URL = os.getenv("MONGODB_URL")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "grocery_finder")

class PriceEntry(BaseModel):
    store_id: str
    product_id: str
    price: float
    currency: str = "USD"
    timestamp: datetime
    unit: Optional[str] = None
    quantity: Optional[float] = None

class Store(BaseModel):
    id: str
    name: str
    location: str
    address: str

class Product(BaseModel):
    id: str
    name: str
    category: str
    brand: Optional[str] = None
    description: Optional[str] = None

@app.on_event("startup")
async def startup_db_client():
    app.mongodb_client = AsyncIOMotorClient(MONGODB_URL)
    app.mongodb = app.mongodb_client[MONGODB_DATABASE]
    try:
        await app.mongodb.command("ping")
        logger.info("Successfully connected to MongoDB")
        await setup_indexes()
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongodb_client.close()

async def setup_indexes():
    await app.mongodb.prices.create_index([
        ("store_id", 1),
        ("product_id", 1),
        ("timestamp", -1)
    ])
    await app.mongodb.stores.create_index("name")
    await app.mongodb.products.create_index("name")

@app.get("/health")
async def health_check():
    try:
        await app.mongodb.command("ping")
        return {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "database": "connected",
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed",
        )

@app.post("/prices", response_model=PriceEntry)
async def create_price_entry(price_entry: PriceEntry):
    try:
        result = await app.mongodb.prices.insert_one(price_entry.model_dump())
        created_entry = await app.mongodb.prices.find_one({"_id": result.inserted_id})
        return PriceEntry(**created_entry)
    except Exception as e:
        logger.error(f"Failed to create price entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create price entry",
        )

@app.get("/prices/compare/{product_id}")
async def compare_prices(product_id: str):
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
        
        prices = await app.mongodb.prices.aggregate(pipeline).to_list(None)
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

@app.get("/products/search")
async def search_products(query: str):
    try:
        cursor = app.mongodb.products.find(
            {"name": {"$regex": query, "$options": "i"}},
            limit=10
        )
        products = await cursor.to_list(None)
        return products
    except Exception as e:
        logger.error(f"Failed to search products: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search products",
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003, reload=True)