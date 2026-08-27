from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SQLite by default so the app runs with no external services.
    # For Postgres: DATABASE_URL=postgresql+asyncpg://xlb:xlb@localhost:5432/xlb
    database_url: str = "sqlite+aiosqlite:///./xlb.db"

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Scraping
    scrape_timeout: float = 20.0
    scrape_retries: int = 3
    scrape_delay_seconds: float = 1.5
    scrape_concurrency: int = 4

    # Scheduler
    enable_scheduler: bool = False
    refresh_interval_hours: int = 6

    # Matching: listings below this confidence are hidden from the public price table
    match_confidence_threshold: float = 0.85


@lru_cache
def get_settings() -> Settings:
    return Settings()
