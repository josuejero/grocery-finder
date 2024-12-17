# app/routers/users/__init__.py
from fastapi import APIRouter
from .profile import router as profile_router
from .shopping_lists import router as shopping_lists_router

router = APIRouter()
router.include_router(profile_router, tags=["profile"])
router.include_router(shopping_lists_router, prefix="/shopping-lists", tags=["shopping"])

__all__ = ["router"]