import logging
import os
import sys
from datetime import datetime, UTC
from typing import Dict, Optional
import httpx
import jwt
import redis.asyncio as redis 
from fastapi import Depends, FastAPI, HTTPException, Request, status, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from prometheus_client import Counter, Histogram
from pydantic import BaseModel, EmailStr
from pathlib import Path

# Create log directory if it doesn't exist
log_dir = Path("/var/log/api_gateway")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.FileHandler("/var/log/api_gateway/api_gateway.log"),
        logging.StreamHandler(sys.stdout)
    ],
)
logger = logging.getLogger(__name__)

class User(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(User):
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginCredentials(BaseModel):
    username: str
    password: str

class ServiceResponse(BaseModel):
    status: str
    data: Optional[Dict] = None
    error: Optional[str] = None

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency", ["endpoint"])
RATE_LIMIT_COUNTER = Counter("rate_limit_hits_total", "Total number of rate limit triggers", ["client_ip"])

app = FastAPI(title="Grocery Finder API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_required_env_var(key: str) -> str:
    value = os.getenv(key)
    if not value:
        error_msg = f"Required environment variable {key} is not set"
        logger.critical(error_msg)
        raise ValueError(error_msg)
    return value

try:
    AUTH_SERVICE_URL = "http://auth_service:8000"
    USER_SERVICE_URL = "http://user_service:8000"
    PRICE_SERVICE_URL = "http://price_service:8000"
    JWT_SECRET_KEY = get_required_env_var("JWT_SECRET_KEY")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    REDIS_URL = "redis://redis:6379"
except ValueError as e:
    logger.critical(f"Failed to initialize environment variables: {e}")
    sys.exit(1)

redis_client = None
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class RateLimitExceeded(Exception):
    pass

@app.on_event("startup")
async def startup_event():
    global redis_client
    logger.info("Starting API Gateway")
    try:
        logger.debug(f"Connecting to Redis at {REDIS_URL}")
        redis_client = redis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5.0
        )
        await redis_client.ping()
        logger.info("Successfully connected to Redis")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        redis_client = None

@app.on_event("shutdown")
async def shutdown_event():
    if redis_client:
        await redis_client.close()
    logger.info("API Gateway shutdown complete")

async def verify_token(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError as e:
        logger.error(f"JWT validation error: {e}")
        raise HTTPException(status_code=401, detail="Could not validate token")

@app.get("/health")
async def health_check():
    try:
        services_status = {}
        async with httpx.AsyncClient(timeout=5.0) as client:
            for name, url in {
                "auth": AUTH_SERVICE_URL,
                "user": USER_SERVICE_URL,
                "price": PRICE_SERVICE_URL
            }.items():
                try:
                    response = await client.get(f"{url}/health")
                    services_status[name] = "healthy" if response.status_code == 200 else "unhealthy"
                except Exception as e:
                    logger.error(f"Health check failed for {name} service: {e}")
                    services_status[name] = "unavailable"

        redis_status = "unavailable"
        if redis_client:
            try:
                await redis_client.ping()
                redis_status = "healthy"
            except Exception as e:
                logger.error(f"Redis health check failed: {e}")

        services_status["redis"] = redis_status
        overall_status = "healthy" if all(s == "healthy" for s in services_status.values()) else "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.now(UTC).isoformat(),
            "version": "1.0.0",
            "services": services_status
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "version": "1.0.0",
            "error": str(e)
        }

# In the section where routes are defined, make sure you have:

@app.post("/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AUTH_SERVICE_URL}/token",  # Note: This maps /auth/login to /token
                data={
                    "username": form_data.username,
                    "password": form_data.password,
                    "grant_type": form_data.grant_type or "password"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.json().get("detail", "Authentication failed")
                )
                
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Auth service request failed: {e}")
        raise HTTPException(status_code=503, detail="Auth service unavailable")




@app.post("/auth/register", response_model=User)
async def register(user: UserCreate):
    logger.debug(f"Registration attempt for user: {user.username}")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{AUTH_SERVICE_URL}/register",
                json=user.model_dump(),
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 400:
                raise HTTPException(
                    status_code=400,
                    detail=response.json().get("detail", "Registration failed")
                )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Registration failed"
                )

            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Auth service request failed: {e}")
        raise HTTPException(status_code=503, detail="Auth service unavailable")
    
@app.post("/users/sync")
async def sync_user(
    username: str,
    authorization: str = Header(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{USER_SERVICE_URL}/users/sync?username={username}",
                headers={"Authorization": authorization}
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"User service sync request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User service unavailable"
        )

@app.get("/users/me")
async def get_user_profile(authorization: str = Header(...)):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{USER_SERVICE_URL}/users/me",
                headers={"Authorization": authorization}
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"User service request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User service unavailable"
        )

@app.post("/users/me/shopping-lists")
async def create_shopping_list(
    shopping_list: dict,
    authorization: str = Header(...),
):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{USER_SERVICE_URL}/users/me/shopping-lists",
                headers={"Authorization": authorization},
                json=shopping_list
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"User service request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User service unavailable"
        )

@app.get("/users/me/shopping-lists")
async def get_shopping_lists(authorization: str = Header(...)):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{USER_SERVICE_URL}/users/me/shopping-lists",
                headers={"Authorization": authorization}
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"User service request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User service unavailable"
        )


@app.delete("/users/me/shopping-lists/{list_id}")
async def delete_shopping_list(
    list_id: int,
    authorization: str = Header(...)
):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(
                f"{USER_SERVICE_URL}/users/me/shopping-lists/{list_id}",
                headers={"Authorization": authorization}
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shopping list not found"
            )
        logger.error(f"User service request failed: {e}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=e.response.text
        )
    except Exception as e:
        logger.error(f"Failed to delete shopping list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.put("/users/me/shopping-lists/{list_id}")
async def update_shopping_list(
    list_id: int,
    shopping_list: dict,
    authorization: str = Header(...)
):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.put(
                f"{USER_SERVICE_URL}/users/me/shopping-lists/{list_id}",
                headers={"Authorization": authorization},
                json=shopping_list
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shopping list not found"
            )
        logger.error(f"User service request failed: {e}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=e.response.text
        )
    except Exception as e:
        logger.error(f"Failed to update shopping list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
        
# Previous imports and code remain the same...

# Add after other endpoints
@app.post("/prices")
async def create_price_entry(price_entry: dict):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{PRICE_SERVICE_URL}/prices",
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

@app.get("/prices/compare/{product_id}")
async def compare_prices(product_id: str):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{PRICE_SERVICE_URL}/prices/compare/{product_id}"
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Price service request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Price service unavailable"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)