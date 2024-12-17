from fastapi import APIRouter, HTTPException, status
import httpx

from app.core.config import settings
from app.core.logging import logger

router = APIRouter()

@router.post("")
async def create_price_entry(price_entry: dict):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.PRICE_SERVICE_URL}/prices",
                json=price_entry
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Price service request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Price service unavailable"
        )

@router.get("/compare/{product_id}")
async def compare_prices(product_id: str):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.PRICE_SERVICE_URL}/prices/compare/{product_id}"
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Price service request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Price service unavailable"
        )