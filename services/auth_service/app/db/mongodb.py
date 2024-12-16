# services/auth_service/db/mongodb.py

import logging
from motor.motor_asyncio import AsyncIOMotorClient
from tenacity import retry, stop_after_attempt, wait_exponential
from fastapi import FastAPI
from contextlib import asynccontextmanager
import os
import sys
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger(__name__)

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def connect_to_mongo() -> AsyncIOMotorClient:
    client = AsyncIOMotorClient(
        settings.MONGODB_URL,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000
    )
    await client.admin.command('ping')
    return client

async def setup_indexes(db):
    await db.users.create_index("username", unique=True)
    await db.users.create_index("email", unique=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.mongodb_client = await connect_to_mongo()
        app.mongodb = app.mongodb_client[settings.MONGODB_DATABASE]
        logger.info("Successfully connected to MongoDB")
        await setup_indexes(app.mongodb)
        yield
    finally:
        app.mongodb_client.close()
        logger.info("Closed MongoDB connection")
