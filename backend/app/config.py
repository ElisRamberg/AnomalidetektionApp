"""Application configuration management."""

import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application settings
    app_name: str = Field(default="Anomaly Detection API", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")

    # Database settings
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/anomaly_detection",
        env="DATABASE_URL",
    )
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")

    # Redis settings for Celery
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

    # File upload settings
    max_file_size: int = Field(default=100 * 1024 * 1024, env="MAX_FILE_SIZE")  # 100MB
    upload_dir: str = Field(default="./uploads", env="UPLOAD_DIR")
    allowed_file_types: list[str] = Field(
        default=["csv", "json", "xlsx", "xls", "xml", "sie4"], env="ALLOWED_FILE_TYPES"
    )

    # Data processing settings
    max_transaction_amount: Optional[float] = Field(
        default=1000000.0, env="MAX_TRANSACTION_AMOUNT"
    )  # 1M default limit

    # API settings
    api_v1_prefix: str = Field(default="/api/v1", env="API_V1_PREFIX")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"], env="CORS_ORIGINS"
    )

    # Security settings
    secret_key: str = Field(
        default="your-secret-key-change-in-production", env="SECRET_KEY"
    )
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # Celery settings
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1", env="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND"
    )

    # Logging settings
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")  # json or console

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings
