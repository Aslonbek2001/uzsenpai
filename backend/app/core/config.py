"""app/core/config.py — the only place that reads environment variables."""

from functools import lru_cache
from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "local-dev-only-jwt-secret-change-me-0000"  # noqa: S105 — refused outside local/test


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Required, no default: a deployment that forgets ENV must fail to start, not silently run as "local".
    env: Literal["local", "test", "staging", "production"]
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    database_url: str = "postgresql+asyncpg://uzsenpai:uzsenpai@localhost:5432/uzsenpai"
    db_pool_size: int = 10
    db_max_overflow: int = 10

    # Redis DB indexes: 0 = app cache/rate limits/auth codes, 1 = Taskiq broker, 2 = bot FSM (bot's own setting)
    redis_url: str = "redis://localhost:6379/0"
    taskiq_broker_url: str = "redis://localhost:6379/1"

    cors_origins: list[str] = ["http://localhost:5173"]
    public_web_url: str = "http://localhost:5173"  # the website (redirect targets after OAuth)
    public_api_url: str = "http://localhost:8000"  # this API as browsers reach it (OAuth callback URL)

    # Auth (ADR 0007)
    jwt_secret: str = DEV_JWT_SECRET
    refresh_cookie_secure: bool = True  # False only for plain-http local development
    telegram_bot_token: str = ""  # verifies Telegram Login Widget data
    bot_service_token: str = ""  # the bot's credential for /api/v1 (with X-Telegram-User-Id)
    google_client_id: str = ""  # Google sign-in is disabled (503) until both are set
    google_client_secret: str = ""

    @property
    def google_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def is_local(self) -> bool:
        """Dev/test only features (fake payment provider, skeleton adapters) are allowed only here."""
        return self.env in ("local", "test")

    @model_validator(mode="after")
    def _refuse_unsafe_deployments(self) -> Self:
        if self.is_local:
            return self
        problems = []
        if self.jwt_secret == DEV_JWT_SECRET or len(self.jwt_secret) < 32:
            problems.append("JWT_SECRET must be a random value of at least 32 characters")
        if len(self.bot_service_token) < 32:
            problems.append("BOT_SERVICE_TOKEN must be a random value of at least 32 characters")
        if not self.telegram_bot_token:
            problems.append("TELEGRAM_BOT_TOKEN is required")
        if "*" in self.cors_origins:
            problems.append("CORS_ORIGINS must list exact origins (credentials are allowed)")
        if not self.refresh_cookie_secure:
            problems.append("REFRESH_COOKIE_SECURE must be true outside local/test")
        if problems:
            raise ValueError("; ".join(problems))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # values (incl. required ENV) come from the environment


settings = get_settings()
