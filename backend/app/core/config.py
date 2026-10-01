"""app/core/config.py — the only place that reads environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Required, no default: a deployment that forgets ENV must fail to start, not silently run as "local".
    env: Literal["local", "test", "staging", "production"]
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    database_url: str = "postgresql+asyncpg://uzsenpai:uzsenpai@localhost:5432/uzsenpai"
    db_pool_size: int = 10
    db_max_overflow: int = 10

    # Redis DB indexes: 0 = app cache/rate limits, 1 = Taskiq broker, 2 = bot FSM (bot's own setting)
    redis_url: str = "redis://localhost:6379/0"
    taskiq_broker_url: str = "redis://localhost:6379/1"

    cors_origins: list[str] = ["http://localhost:5173"]
    public_web_url: str = "http://localhost:5173"

    @property
    def is_local(self) -> bool:
        """Dev/test only features (fake payment provider, skeleton adapters) are allowed only here."""
        return self.env in ("local", "test")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # values (incl. required ENV) come from the environment


settings = get_settings()
