from functools import lru_cache
from typing import List

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

    # Comma-separated origins (avoid JSON list env parsing issues)
    backend_cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:3001,http://127.0.0.1:3001"
    )

    database_url: str = "postgresql+asyncpg://scholarship:scholarship@localhost:5435/scholarship_autopilot"
    database_url_sync: str = "postgresql://scholarship:scholarship@localhost:5435/scholarship_autopilot"

    redis_url: str = "redis://localhost:6381/0"
    celery_broker_url: str = "redis://localhost:6381/0"
    celery_result_backend: str = "redis://localhost:6381/1"

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

    reminder_intervals_days: str = "60,30,14,7,3,1,0"

    scraper_timeout_seconds: float = 20.0
    scraper_max_retries: int = 3
    scraper_rate_limit_per_domain: float = 1.0

    @property
    def cors_origins(self) -> List[str]:
        value = self.backend_cors_origins.strip()
        if not value:
            return ["http://localhost:3000", "http://localhost:3001"]
        if value.startswith("["):
            import json

            try:
                return list(json.loads(value))
            except json.JSONDecodeError:
                # Fallback for unquoted list-like strings
                inner = value.strip("[]")
                return [origin.strip().strip("'\"") for origin in inner.split(",") if origin.strip()]
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @property
    def reminder_intervals(self) -> List[int]:
        return [int(x.strip()) for x in self.reminder_intervals_days.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
