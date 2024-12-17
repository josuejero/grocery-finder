# app/core/logging.py
import logging
import sys
from pathlib import Path
from app.core.config import settings

LOG_DIR = Path("/var/log/api_gateway")
LOG_FILE = LOG_DIR / "api_gateway.log"

def setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    )

    # File handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG if settings.debug else logging.INFO)

    # Setup logger
    logger = logging.getLogger("api_gateway")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

# Initialize logger
logger = setup_logging()
