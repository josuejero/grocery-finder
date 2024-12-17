from fastapi import APIRouter
from .auth import router as auth_router
from .users import router as users_router
from .prices import router as prices_router

# Create routers with their prefixes
auth = APIRouter()
auth.include_router(auth_router, prefix="/auth", tags=["auth"])

users = APIRouter()
users.include_router(users_router, prefix="/users", tags=["users"])

prices = APIRouter()
prices.include_router(prices_router, prefix="/prices", tags=["prices"])

# Export routers
__all__ = ["auth", "users", "prices"]