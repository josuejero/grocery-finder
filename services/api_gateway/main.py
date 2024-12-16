import logging
import os
import sys
from datetime import datetime, UTC
from typing import Dict, Optional
import httpx
import jwt
import redis.asyncio as redis 
from fastapi import FastAPI, Request, HTTPException, status, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseSettings

import signal

def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}")
    raise SystemExit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Create log directory if it doesn't exist
log_dir = Path("/var/log/api_gateway")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    AUTH_SERVICE_URL: str = "http://auth_service:8000"
    USER_SERVICE_URL: str = "http://user_service:8000" 
    PRICE_SERVICE_URL: str = "http://price_service:8000"
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    RATE_LIMIT_PER_MINUTE: int = 60
    REDIS_URL: str = "redis://redis:6379"

    class Config:
        env_file = ".env"

settings = Settings()



def get_settings() -> Settings:
    required_vars = ["JWT_SECRET_KEY"]
    for var in required_vars:
        if var not in os.environ:
            logger.critical(f"Environment variable {var} is not set.")
            sys.exit(1)
    return Settings(
        AUTH_SERVICE_URL=os.getenv("AUTH_SERVICE_URL", "http://localhost:8001"),
        USER_SERVICE_URL=os.getenv("USER_SERVICE_URL", "http://localhost:8002"),
        PRICE_SERVICE_URL=os.getenv("PRICE_SERVICE_URL", "http://localhost:8003"),
        JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY"),
        JWT_ALGORITHM=os.getenv("JWT_ALGORITHM", "HS256"),
        RATE_LIMIT_PER_MINUTE=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
        REDIS_URL=os.getenv("REDIS_URL", "redis://localhost:6379"),
    )


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

app = FastAPI(title="API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = None


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
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

class RateLimitExceeded(Exception):
    pass

@app.on_event("startup")
async def startup_event():
    global redis_client
    logger.info("Starting API Gateway")
    try:
        logger.debug(f"Connecting to Redis at {settings.REDIS_URL}")
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
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
    services_status = {}
    async with httpx.AsyncClient() as client:
        for name, url in {
            "auth": settings.AUTH_SERVICE_URL,
            "user": settings.USER_SERVICE_URL,
            "price": settings.PRICE_SERVICE_URL
        }.items():
            try:
                response = await client.get(f"{url}/health")
                services_status[name] = "healthy" if response.status_code == 200 else "unhealthy"
            except Exception as e:
                logger.error(f"Health check failed for {name} service: {e}")
                services_status[name] = "unavailable"

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": services_status
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
    try:
        # 1. Register with auth service
        async with httpx.AsyncClient(timeout=10.0) as client:
            auth_response = await client.post(
                f"{AUTH_SERVICE_URL}/register",
                json=user.model_dump(),
                headers={"Content-Type": "application/json"}
            )
            
            if auth_response.status_code != 200:
                raise HTTPException(
                    status_code=auth_response.status_code,
                    detail=auth_response.text
                )
                
            auth_user = auth_response.json()
            
            # 2. Get JWT token for user sync
            login_response = await client.post(
                f"{AUTH_SERVICE_URL}/token",  # Changed from /login to /token
                data={
                    "username": user.username,
                    "password": user.password,
                    "grant_type": "password"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )   
            
            if login_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get auth token for sync"
                )
            
            token = login_response.json()["access_token"]

            # 3. Sync with user service
            sync_response = await client.post(
                f"{USER_SERVICE_URL}/users/sync",
                params={"username": user.username},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )
            
            if sync_response.status_code != 200:
                logger.error(f"User sync failed: {sync_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to sync user"
                )

            return auth_user

    except httpx.RequestError as e:
        logger.error(f"Service request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )

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

# In services/api_gateway/main.py - Add these imports if not present
import traceback
import socket
import dns.resolver

@app.get("/users/me")
async def get_user_profile(authorization: str = Header(None)):
    if not authorization:
        logger.error("Authorization header missing")
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    try:
        logger.debug(f"Attempting to reach User Service at: {USER_SERVICE_URL}")
        logger.debug(f"Authorization header: {authorization[:50]}...")
        
        # DNS check
        parsed_url = urllib.parse.urlparse(USER_SERVICE_URL)
        hostname = parsed_url.hostname
        try:
            logger.debug(f"Performing DNS lookup for {hostname}")
            ip_addresses = socket.gethostbyname_ex(hostname)
            logger.debug(f"DNS Resolution results:")
            logger.debug(f"  Canonical name: {ip_addresses[0]}")
            logger.debug(f"  IP Addresses: {ip_addresses[2]}")
        except socket.gaierror as e:
            logger.error(f"DNS resolution failed for {hostname}: {e}")
            # Try additional DNS checks
            try:
                resolver = dns.resolver.Resolver()
                answers = resolver.resolve(hostname, 'A')
                logger.debug(f"Alternative DNS lookup results:")
                for rdata in answers:
                    logger.debug(f"  IP Address: {rdata}")
            except Exception as dns_e:
                logger.error(f"Alternative DNS lookup failed: {dns_e}")

        # Test User Service health before making the actual request
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                health_response = await client.get(f"{USER_SERVICE_URL}/health")
                logger.debug(f"User Service health check response: {health_response.status_code}")
                if health_response.status_code != 200:
                    logger.error(f"User Service health check failed with status: {health_response.status_code}")
                    logger.error(f"Health check response: {health_response.text}")
            except Exception as e:
                logger.error(f"User Service health check failed: {e}")
                logger.error(f"Health check error details: {traceback.format_exc()}")
            
            # Make the actual request
            try:
                response = await client.get(
                    f"{USER_SERVICE_URL}/users/me",
                    headers={"Authorization": authorization},
                    timeout=10.0
                )
                logger.debug(f"User Service response status: {response.status_code}")
                logger.debug(f"User Service response headers: {dict(response.headers)}")
                
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException as e:
                logger.error(f"Request timed out: {e}")
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=f"Request to User Service timed out: {str(e)}"
                )
            except httpx.HTTPError as e:
                logger.error(f"HTTP error: {e}")
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"User Service error: {e.response.text}"
                )
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unavailable: {str(e)}"
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

@app.get("/users/me/shopping-lists/{list_id}")
async def get_shopping_list(
    list_id: int,
    authorization: str = Header(...),
):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{USER_SERVICE_URL}/users/me/shopping-lists/{list_id}",
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

@app.get("/users/me/shopping-lists")
async def get_shopping_lists(authorization: str = Header(...)):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            logger.debug(f"Forwarding shopping lists request with auth: {authorization}")
            response = await client.get(
                f"{USER_SERVICE_URL}/users/me/shopping-lists",
                headers={"Authorization": authorization}
            )
            logger.debug(f"Shopping lists response: {response.status_code}")
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

@app.middleware("http")
async def token_validation_middleware(request: Request, call_next):
    logger.debug(f"Request path: {request.url.path}")
    logger.debug(f"Request headers: {dict(request.headers)}")
    
    auth_header = request.headers.get('Authorization')
    if auth_header:
        try:
            token = auth_header.split(' ')[1]
            logger.debug(f"Validating token: {token[:20]}...")
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            logger.debug(f"Token valid for user: {payload.get('sub')}")
        except Exception as e:
            logger.error(f"Token validation failed: {str(e)}")
            logger.error(traceback.format_exc())
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid authentication token"}
            )

    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Request failed: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except HTTPException as exc:
        logger.error(f"HTTP Exception: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    except Exception as exc:
        logger.error(f"Unhandled exception: {str(exc)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code} for {request.method} {request.url}")
    return response


# Error Handling Middleware
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTPException: {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

@app.get("/health")
async def health_check():
    try:
        # For services using MongoDB
        await app.mongodb.command("ping")
        return {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )

from fastapi.responses import JSONResponse
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug",
    )