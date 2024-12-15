import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.database import init_db, Base
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.database import init_db

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

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:3000"],  # Allow API Gateway and Frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Authorization"],
)

app.include_router(router)

# Add these imports at the top
import socket
import psutil
from datetime import datetime, UTC

@app.get("/health")
async def health_check():
    try:
        # Check database connection
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            
        # Get system metrics
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get network info
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "database": "connected",
            "hostname": hostname,
            "ip_address": ip_address,
            "system_metrics": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": memory.percent,
                "disk_percent": disk.percent
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "error": str(e),
            "traceback": traceback.format_exc()
        }

# Run the User Service
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,  # Ensure this port matches the API Gateway's USER_SERVICE_URL
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )