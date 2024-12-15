# services/user_service/app/api/endpoints/health.py

from datetime import datetime, UTC
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.database import get_db
from app.core.logging import logger

router = APIRouter(tags=["health"])

@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        
        # Return detailed health information
        return {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "database": "connected",
            "service": "user_service",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )