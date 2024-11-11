from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Database settings
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = None

    # JWT settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # MongoDB settings
    MONGODB_URL: str
    MONGODB_DATABASE: str

    # Redis settings
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://redis:6379"

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Security
    BCRYPT_SALT_ROUNDS: int = 12

    # Service URLs
    AUTH_SERVICE_URL: str = "http://auth_service:8000"
    USER_SERVICE_URL: str = "http://user_service:8000"
    PRICE_SERVICE_URL: str = "http://price_service:8000"

    # Logging
    LOG_LEVEL: str = "DEBUG"

    # CORS settings
    CORS_ORIGINS: list = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )

    @property
    def sync_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

@lru_cache()
def get_settings() -> Settings:
    return Settings()