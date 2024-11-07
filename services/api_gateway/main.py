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
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from prometheus_client import Counter, Histogram
from pydantic import BaseModel

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
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
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

redis_client = None

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
    

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    global redis_client
    logger.info("Starting API Gateway")
    
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
    redis_client = redis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    
    try:
        await redis_client.ping()
        logger.info("Successfully connected to Redis")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
    
    await check_service_health()

@app.on_event("shutdown")
async def shutdown_event():
    if redis_client:
        await redis_client.close()
        logger.info("Closed Redis connection")

async def check_service_health():
    services = {
        "auth": AUTH_SERVICE_URL,
        "user": USER_SERVICE_URL,
        "price": PRICE_SERVICE_URL
    }
    
    async with httpx.AsyncClient() as client:
        for name, url in services.items():
            try:
                response = await client.get(f"{url}/health", timeout=5.0)
                if response.status_code == 200:
                    logger.info(f"{name} service is healthy")
                else:
                    logger.error(f"{name} service health check failed: {response.status_code}")
            except Exception as e:
                logger.error(f"Failed to connect to {name} service: {str(e)}")

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    logger.debug(f"Processing request: {request.method} {request.url.path}")

    if getattr(app.state, "testing", False):
        logger.debug("Testing mode detected, skipping rate limiting")
        return await call_next(request)

    if not redis_client:
        logger.warning("Redis client not available, skipping rate limiting")
        return await call_next(request)

    try:
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
    except redis.ConnectionError as e:
        logger.error(f"Redis connection error: {str(e)}")
        return await call_next(request)
    except Exception as e:
        logger.error(f"Rate limit middleware error: {str(e)}")
        return await call_next(request)

async def validate_token(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError as e:
        logger.error(f"JWT validation error: {str(e)}")
        raise HTTPException(status_code=401, detail="Could not validate token")

@app.get("/health")
async def health_check():
    logger.debug("Health check requested")
    try:
        services_status = {}
        
        async with httpx.AsyncClient() as client:
            for name, url in {
                "auth": AUTH_SERVICE_URL,
                "user": USER_SERVICE_URL,
                "price": PRICE_SERVICE_URL
            }.items():
                try:
                    response = await client.get(f"{url}/health", timeout=5.0)
                    services_status[name] = "healthy" if response.status_code == 200 else "unhealthy"
                except Exception as e:
                    logger.error(f"Health check failed for {name} service: {str(e)}")
                    services_status[name] = "unavailable"

        if redis_client:
            try:
                await redis_client.ping()
                services_status["redis"] = "healthy"
            except Exception as e:
                logger.error(f"Redis health check failed: {str(e)}")
                services_status["redis"] = "unavailable"
        else:
            services_status["redis"] = "unavailable"

        overall_status = "healthy" if all(s == "healthy" for s in services_status.values()) else "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.now(UTC).isoformat(),
            "version": "1.0.0",
            "services": services_status
        }
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "version": "1.0.0",
            "error": str(e)
        }

@app.post("/auth/register")
async def register(user: UserCreate):
    logger.debug(f"Registration attempt for user: {user.username}")
    REQUEST_COUNT.labels(method="POST", endpoint="/auth/register").inc()

    try:
        async with httpx.AsyncClient() as client:
            auth_register_url = f"{AUTH_SERVICE_URL}/register"
            logger.debug(f"Forwarding register request to auth service: {auth_register_url}")
            
            response = await client.post(
                auth_register_url,
                json=user.model_dump(),
                timeout=10.0
            )

            response_data = response.json()
            logger.debug(f"Auth service registration response: {response.status_code}")

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response_data.get("detail", "Registration failed"),
                )

            return response_data

    except httpx.RequestError as e:
        logger.error(f"Auth service request failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Auth service unavailable")
    except HTTPException as e:
        logger.warning(f"Registration failed: {str(e.detail)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/auth/login")
async def login(credentials: LoginCredentials):
    logger.debug(f"Login attempt for user: {credentials.username}")
    REQUEST_COUNT.labels(method="POST", endpoint="/auth/login").inc()

    try:
        async with httpx.AsyncClient() as client:
            auth_login_url = f"{AUTH_SERVICE_URL}/login"
            logger.debug(f"Forwarding login request to auth service: {auth_login_url}")
            
            # Convert to form data as expected by the auth service
            form_data = {
                "username": credentials.username,
                "password": credentials.password,
                "grant_type": "password"
            }
            
            response = await client.post(
                auth_login_url,
                data=form_data,  # Using form data instead of JSON
                timeout=10.0
            )

            response_data = response.json()
            logger.debug(f"Auth service response status: {response.status_code}")

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