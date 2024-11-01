import logging
import os
import sys
import traceback
from datetime import UTC, datetime
from functools import lru_cache
from typing import Dict, Optional

import httpx
import jwt
import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from prometheus_client import Counter, Histogram
from pydantic import BaseModel

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("api_gateway.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Grocery Finder API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth_service:8000")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user_service:8000")
PRICE_SERVICE_URL = os.getenv("PRICE_SERVICE_URL", "http://price_service:8000")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default-secret-key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint"]
)
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class LoginCredentials(BaseModel):
    username: str
    password: str


class ServiceResponse(BaseModel):
    status: str
    data: Optional[Dict] = None
    error: Optional[str] = None


@lru_cache()
def get_redis_client():
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
    return redis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=True,
    )


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    logger.debug(f"Processing request: {request.method} {request.url.path}")

    if getattr(app.state, "testing", False):
        logger.debug("Testing mode detected, skipping rate limiting")
        return await call_next(request)

    try:
        redis_client = get_redis_client()
        client_ip = request.client.host
        key = f"rate_limit:{client_ip}"

        requests = await redis_client.incr(key)
        if requests == 1:
            await redis_client.expire(key, 60)

        if requests > RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
            )

        response = await call_next(request)
        return response
    except redis.ConnectionError:
        return await call_next(request)


async def validate_token(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Could not validate token")


@app.get("/health")
async def health_check():
    logger.debug("Health check requested")
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "1.0.0",
    }


@app.post("/auth/login")
async def login(credentials: LoginCredentials):
    logger.debug(f"Login attempt for user: {credentials.username}")
    REQUEST_COUNT.labels(method="POST", endpoint="/auth/login").inc()

    try:
        with REQUEST_LATENCY.time():
            async with httpx.AsyncClient() as client:
                auth_login_url = f"{AUTH_SERVICE_URL}/login"
                logger.debug(
                    f"Forwarding login request to auth service: {auth_login_url}"
                )
                response = await client.post(
                    auth_login_url,
                    json=credentials.model_dump(),
                )

                response_data = response.json()
                logger.debug(f"Auth service response: {response.status_code}")

                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=response_data.get("detail", "Authentication failed"),
                    )

                return response_data

    except httpx.RequestError as e:
        logger.error(f"Auth service request failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Auth service unavailable")
    except HTTPException as e:
        logger.warning(f"Authentication failed: {str(e.detail)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
