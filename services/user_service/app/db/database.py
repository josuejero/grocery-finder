# services/user_service/app/core/database.py

import logging
import sys
import time
from typing import AsyncGenerator, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()

# Create the declarative base
Base = declarative_base()

def get_engine():
    database_url = settings.sync_database_url
    logger.info(f"Connecting to database: {database_url}")
    return create_engine(
        database_url,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_pre_ping=True
    )

def get_session_maker():
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=get_engine()
    )

# Add Async support
async_engine = create_async_engine(
    settings.sync_database_url.replace('postgresql://', 'postgresql+asyncpg://'),
    echo=True,
)

# Use sessionmaker directly with AsyncSession
async_session = sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def init_db(retries=5, delay=5) -> Tuple[object, object]:
    last_exception = None
    
    for attempt in range(retries):
        try:
            logger.debug(f"Database connection attempt {attempt + 1}/{retries}")
            
            engine = get_engine()
            SessionLocal = get_session_maker()
            
            # Test the connection
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).scalar()
                logger.debug(f"Database test query result: {result}")
            
            # Create tables
            Base.metadata.create_all(bind=engine)
            logger.info("Database initialized successfully")
            
            return engine, SessionLocal
            
        except OperationalError as e:
            last_exception = e
            logger.error(f"Database connection error on attempt {attempt + 1}: {e}")
            if attempt < retries - 1:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
        except Exception as e:
            logger.error(f"Unexpected database initialization error: {e}", exc_info=True)
            raise

    logger.error("Max retries reached, cannot connect to database")
    raise last_exception

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
