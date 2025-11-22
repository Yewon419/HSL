from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://admin:admin123@postgres:5432/stocktrading"
    REDIS_URL: str = "redis://redis:6379"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    INFLUXDB_URL: str = "http://influxdb:8086"
    INFLUXDB_TOKEN: str = "my-super-secret-auth-token"
    INFLUXDB_ORG: str = "stocktrading"
    INFLUXDB_BUCKET: str = "metrics"

    JWT_SECRET_KEY: str = "your-secret-key-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    YAHOO_FINANCE_API_KEY: Optional[str] = None

    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8080",
        "http://192.168.219.102:8000",
        "http://192.168.219.102:8080"
    ]

    class Config:
        # Use environment variables, then fall back to .env file
        env_file = ".env" if os.path.exists(".env") else None
        case_sensitive = True

settings = Settings()