# services/price_service/app/core/mongodb.py
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import settings
from .logging import logger

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

mongodb = MongoDB()

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def connect_to_mongo() -> AsyncIOMotorClient:
    """Connect to MongoDB with retry logic"""
    try:
        client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            maxPoolSize=settings.DB_MAX_CONNECTIONS,
            serverSelectionTimeoutMS=settings.DB_SERVER_SELECTION_TIMEOUT,
            connectTimeoutMS=settings.DB_CONNECTION_TIMEOUT
        )
        # Verify the connection
        await client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

async def get_database():
    """Dependency to get database connection"""
    if mongodb.client is None:
        mongodb.client = await connect_to_mongo()
        mongodb.db = mongodb.client[settings.MONGODB_DATABASE]
    return mongodb.db

async def close_mongo_connection():
    """Close MongoDB connection"""
    if mongodb.client:
        mongodb.client.close()
        mongodb.client = None
        logger.info("Closed MongoDB connection")

async def init_indexes():
    """Initialize MongoDB indexes"""
    db = mongodb.client[settings.MONGODB_DATABASE]
    try:
        # Prices collection indexes
        await db.prices.create_index([
            ("store_id", 1),
            ("product_id", 1),
            ("timestamp", -1)
        ])
        await db.prices.create_index([("product_id", 1)])
        await db.prices.create_index([("timestamp", -1)])

        # Products collection indexes
        await db.products.create_index([("id", 1)], unique=True)
        await db.products.create_index([("name", "text")])
        await db.products.create_index([("category", 1)])

        # Stores collection indexes
        await db.stores.create_index([("id", 1)], unique=True)
        await db.stores.create_index([("location", "2dsphere")])
        await db.stores.create_index([("active", 1)])

        logger.info("Successfully initialized MongoDB indexes")
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")
        raise

async def connect_db(app: FastAPI):
    """Connect to MongoDB on application startup"""
    try:
        mongodb.client = await connect_to_mongo()
        mongodb.db = mongodb.client[settings.MONGODB_DATABASE]
        await init_indexes()
        
        # Store MongoDB client in app state
        app.state.mongodb = mongodb
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB: {e}")
        raise

async def close_db(app: FastAPI):
    """Close MongoDB connection on application shutdown"""
    try:
        if mongodb.client:
            mongodb.client.close()
            logger.info("Closed MongoDB connection")
    except Exception as e:
        logger.error(f"Error closing MongoDB connection: {e}")