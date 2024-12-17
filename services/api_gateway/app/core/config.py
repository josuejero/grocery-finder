import os
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Service URLs
    AUTH_SERVICE_URL: str = Field(..., env="AUTH_SERVICE_URL")
    USER_SERVICE_URL: str = Field(..., env="USER_SERVICE_URL")
    PRICE_SERVICE_URL: str = Field(..., env="PRICE_SERVICE_URL")

    # JWT Configuration
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Redis Configuration
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")

    # Logging
    LOG_LEVEL: str = "INFO"

    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    
    @classmethod
    def validate_jwt_secret(cls, v):
        if not v or len(v) < 32:
            raise ValueError("JWT secret key must be at least 32 characters long")
        return v

    @classmethod
    def validate_environment(cls, v):
        valid_envs = ["development", "production", "testing"]
        if v.lower() not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}")
        return v.lower()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    """
    Cached method to retrieve application settings
    Ensures settings are only loaded once and cached
    """
    return Settings()

# Global settings instance
settings = get_settings()