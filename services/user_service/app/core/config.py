# services/user_service/app/core/config.py

from typing import List
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, field_validator
from functools import lru_cache

class Settings(BaseSettings):
    # Database settings
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str | None = None

    # JWT settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # MongoDB settings
    MONGODB_URL: str = "mongodb://mongodb:27017"
    MONGODB_DATABASE: str = "grocery_finder"
    
    # Redis settings
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://redis:6379"
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Logging
    LOG_LEVEL: str = "DEBUG"
    
    # Security
    BCRYPT_SALT_ROUNDS: int = 12
    
    # Service URLs
    AUTH_SERVICE_URL: str = "http://auth_service:8000"
    USER_SERVICE_URL: str = "http://user_service:8000"
    PRICE_SERVICE_URL: str = "http://price_service:8000"
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["http://localhost:8000", "http://localhost:3000"]
    
    @field_validator("CORS_ORIGINS", mode='before')
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def sync_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

@lru_cache()
def get_settings() -> Settings:
    return Settings()