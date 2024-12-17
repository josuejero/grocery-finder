# services/price_service/app/core/logging.py
import logging
import sys
from pathlib import Path

from .config import settings

# Create logs directory if it doesn't exist
LOG_DIR = Path("/var/log/price_service")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging format
log_format = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
date_format = "%Y-%m-%d %H:%M:%S"

# Create formatter
formatter = logging.Formatter(log_format, date_format)

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

# Create file handler
file_handler = logging.FileHandler(LOG_DIR / "price_service.log")
file_handler.setFormatter(formatter)

# Create logger
logger = logging.getLogger("price_service")
logger.setLevel(settings.LOG_LEVEL)
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Set up error logging
error_handler = logging.FileHandler(LOG_DIR / "error.log")
error_handler.setFormatter(formatter)
error_handler.setLevel(logging.ERROR)
logger.addHandler(error_handler)

def setup_logger(name: str) -> logging.Logger:
    """Create a logger instance for a specific module"""
    logger = logging.getLogger(name)
    logger.setLevel(settings.LOG_LEVEL)
    
    # Don't add handlers if they already exist
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.addHandler(error_handler)
    
    return logger