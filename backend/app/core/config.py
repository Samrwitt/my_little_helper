from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Scholarship Autopilot"
    environment: str = "development"
    debug: bool = True
    secret_key: str = "change-me-to-a-long-random-secret-key-in-production"

    backend_cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    database_url: str = "postgresql+asyncpg://scholarship:scholarship@localhost:5432/scholarship_autopilot"
    database_url_sync: str = "postgresql://scholarship:scholarship@localhost:5432/scholarship_autopilot"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    jwt_algorithm: str = "HS256"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@scholarship-autopilot.local"

    search_provider: str = "duckduckgo"
    brave_api_key: str = ""

    discover_rate_limit_per_hour: int = 3

    reminder_intervals_days: List[int] = Field(
        default_factory=lambda: [60, 30, 14, 7, 3, 1, 0]
    )

    scraper_timeout_seconds: float = 20.0
    scraper_max_retries: int = 3
    scraper_rate_limit_per_domain: float = 1.0

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                import json

                return json.loads(value)
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
