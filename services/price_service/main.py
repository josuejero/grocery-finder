# services/price_service/main.py
import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import signal

from app.core.mongodb import connect_db, close_db
from app.api import prices, products, stores
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}")
    raise SystemExit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

app = FastAPI(title="Price Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add startup and shutdown events
app.add_event_handler("startup", connect_db)
app.add_event_handler("shutdown", close_db)

# Include routers
app.include_router(prices.router, prefix="/prices", tags=["prices"])
app.include_router(products.router, prefix="/products", tags=["products"])
app.include_router(stores.router, prefix="/stores", tags=["stores"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003, reload=True)