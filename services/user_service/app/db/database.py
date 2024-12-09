import time
from typing import AsyncGenerator, Optional, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()

# Shared instances
engine = None
SessionLocal = None
Base = declarative_base()

def get_engine():
    global engine
    if engine is None:
        engine = create_engine(
            settings.sync_database_url,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_pre_ping=True
        )
    return engine

def get_session_maker():
    global SessionLocal
    if SessionLocal is None:
        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine()
        )
    return SessionLocal

async def init_db(retries=5, delay=5) -> Tuple[object, object]:
    """Initialize database connection."""
    global engine, SessionLocal
    
    for attempt in range(retries):
        try:
            logger.debug(f"Database connection attempt {attempt + 1}/{retries}")
            
            engine = get_engine()
            SessionLocal = get_session_maker()
            
            # Test the connection
            with engine.connect() as conn:
                logger.debug("Testing database connection")
                result = conn.execute(text("SELECT 1")).scalar()
                logger.debug(f"Database test query result: {result}")
            
            # Create tables
            Base.metadata.create_all(bind=engine)
            logger.debug("Created database tables")
            
            return engine, SessionLocal
            
        except OperationalError as e:
            logger.error(f"Database connection error on attempt {attempt + 1}: {e}")
            if attempt < retries - 1:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.error("Max retries reached, cannot connect to database")
                raise
        except Exception as e:
            logger.error(f"Unexpected database initialization error: {e}", exc_info=True)
            raise

def get_db():
    """Dependency for database session."""
    db = None
    try:
        session_maker = get_session_maker()
        db = session_maker()
        yield db
    finally:
        if db is not None:
            db.close()