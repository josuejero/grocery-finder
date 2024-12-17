# main.py
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from datetime import datetime
import httpx
import asyncio

from app.core.config import settings
from app.core.logging import logger
import redis.asyncio as redis
from app.middleware import RateLimiter
from app.middleware.token_validation import token_validation_middleware
from app.middleware.error_handling import error_handling_middleware

# Create FastAPI app
app = FastAPI(
    title="Grocery Finder API Gateway",
    description="API Gateway for Grocery Finder Microservices"
)

# Initialize Redis
redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

# Add Middleware
app.add_middleware(RateLimiter, redis_client=redis_client)
app.middleware("http")(token_validation_middleware)
app.middleware("http")(error_handling_middleware)

# main.py (excerpt)
@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Perform health check on all dependent services
    """
    services = {
        "auth": settings.AUTH_SERVICE_URL,
        "user": settings.USER_SERVICE_URL,
        "price": settings.PRICE_SERVICE_URL
    }
    services_status = {}

    async def check_service(name: str, url: str):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{url}/health", timeout=5.0)
                services_status[name] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception as e:
            logger.error(f"Health check failed for {name} service: {e}")
            services_status[name] = "unavailable"

    # Use asyncio.gather to check all services concurrently
    await asyncio.gather(*(check_service(name, url) for name, url in services.items()))

    overall_status = all(status == "healthy" for status in services_status.values())
    http_status = status.HTTP_200_OK if overall_status else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=http_status,
        content={
            "status": "healthy" if overall_status else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": services_status
        }
    )



# Include routers
from app.routers import auth, users, prices
app.include_router(auth, prefix="/api")
app.include_router(users, prefix="/api")
app.include_router(prices, prefix="/api")