import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import Settings
from app.core.logging import setup_logging
from app.db.database import init_db, Base, engine
from app.core.config import get_settings

settings = get_settings()
logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Initialize database and store engine and SessionLocal on app
        engine, session_local = await init_db()
        app.state.engine = engine
        app.state.session_local = session_local
        logger.info("Database connection established")
        yield
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    finally:
        if hasattr(app.state, "engine"):
            try:
                app.state.engine.dispose()
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")

app = FastAPI(
    title="User Service",
    description="Service for managing user profiles and shopping lists",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

def get_application():
    return app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )