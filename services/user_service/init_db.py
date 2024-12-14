import asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from app.db.models import Base
from app.core.config import get_settings

settings = get_settings()

def init_sync_db():
    """Initialize database using synchronous engine"""
    engine = create_engine(settings.sync_database_url)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully")

if __name__ == "__main__":
    init_sync_db()