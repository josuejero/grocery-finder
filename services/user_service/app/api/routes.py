from fastapi import APIRouter

from app.api.endpoints import health, profiles, shopping_lists
from app.core.logging import logger
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.user import UserProfile
from app.api.dependencies import get_current_user  # Updated this import path
from app.db.models import UserModel 

router = APIRouter()

# Include all routers from endpoints
router.include_router(health.router, prefix="", tags=["health"])
router.include_router(profiles.router, prefix="", tags=["profiles"])
router.include_router(shopping_lists.router, prefix="", tags=["shopping-lists"])

@router.get("/users/me", response_model=UserProfile)
async def get_user_profile(current_user: UserModel = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return current_user

# Log all registered routes
@router.on_event("startup")
async def log_routes():
    route_paths = [
        f"{route.path} [{', '.join(route.methods)}]"
        for route in router.routes
    ]
    logger.info("Registered routes:")
    for path in route_paths:
        logger.info(f"  {path}")