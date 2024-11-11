import logging
import sys
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()

LOG_DIR = Path("/var/log/user_service")
LOG_FILE = LOG_DIR / "user_service.log"
DEBUG_LOG_FILE = LOG_DIR / "debug.log"

def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    )

    main_handler = logging.FileHandler(LOG_FILE)
    main_handler.setLevel(logging.INFO)
    main_handler.setFormatter(formatter)

    debug_handler = logging.FileHandler(DEBUG_LOG_FILE)
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(settings.LOG_LEVEL)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(main_handler)
    logger.addHandler(debug_handler)
    logger.addHandler(console_handler)

    return logger

logger = setup_logging()