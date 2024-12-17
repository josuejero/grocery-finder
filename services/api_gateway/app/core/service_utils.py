# app/core/service_utils.py
import httpx
from fastapi import HTTPException, status
from app.core.logging import logger

def handle_http_error(e: httpx.HTTPError):
    logger.error(f"Service request failed: {e}")
    status_code = e.response.status_code if hasattr(e, 'response') else status.HTTP_503_SERVICE_UNAVAILABLE
    detail = e.response.text if hasattr(e, 'response') else str(e)
    raise HTTPException(status_code=status_code, detail=detail)
