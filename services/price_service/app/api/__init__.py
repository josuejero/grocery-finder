# services/price_service/app/api/__init__.py
from fastapi import APIRouter
from .prices import router as prices_router
from .products import router as products_router
from .stores import router as stores_router

routers = [prices_router, products_router, stores_router]