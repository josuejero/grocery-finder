from functools import lru_cache
import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    MONGODB_URL: str = os.getenv("MONGODB_URL")
    MONGODB_DATABASE: str = os.getenv("MONGODB_DATABASE", "grocery_finder")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours
    BCRYPT_SALT_ROUNDS: int = int(os.getenv("BCRYPT_SALT_ROUNDS", "12"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    class Config:
        case_sensitive = True

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()