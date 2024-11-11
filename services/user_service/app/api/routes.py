from fastapi import APIRouter

from app.api.endpoints import health, profiles, shopping_lists
from app.core.logging import logger

router = APIRouter()

# Include all routers from endpoints
router.include_router(health.router, prefix="", tags=["health"])
router.include_router(profiles.router, prefix="", tags=["profiles"])
router.include_router(shopping_lists.router, prefix="", tags=["shopping-lists"])

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