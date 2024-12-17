# services/price_service/app/core/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # MongoDB settings
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
    MONGODB_DATABASE: str = os.getenv("MONGODB_DATABASE", "grocery_finder")
    
    # Service settings
    SERVICE_NAME: str = "price-service"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:8000",
        "http://localhost:3000"
    ]
    
    # Service URLs
    AUTH_SERVICE_URL: str = os.getenv("AUTH_SERVICE_URL", "http://auth_service:8000")
    USER_SERVICE_URL: str = os.getenv("USER_SERVICE_URL", "http://user_service:8000")
    
    # Database connection settings
    DB_MAX_CONNECTIONS: int = 10
    DB_CONNECTION_TIMEOUT: int = 5000  # ms
    DB_SERVER_SELECTION_TIMEOUT: int = 5000  # ms

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()