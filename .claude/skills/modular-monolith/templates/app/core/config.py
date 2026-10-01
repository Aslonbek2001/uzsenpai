"""app/core/config.py — the only place that reads environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Required, no default: a deployment that forgets ENV must fail to start, not silently run as "local".
    env: Literal["local", "test", "staging", "production"]
    database_url: str = "postgresql+asyncpg://uzsenpai:uzsenpai@localhost:5432/uzsenpai"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = ["http://localhost:5173"]

    public_web_url: str = "http://localhost:5173"  # where providers send the user back after paying

    # Payments — only providers listed here are active (see billing.public.build_provider_registry)
    payment_providers_enabled: list[str] = []  # e.g. ["payme", "click"] in production, ["fake"] locally
    payme_merchant_id: str = ""
    payme_key: str = ""
    payme_checkout_url: str = "https://checkout.paycom.uz"
    click_service_id: str = ""
    click_merchant_id: str = ""
    click_secret_key: str = ""
    click_checkout_url: str = "https://my.click.uz/services/pay"
    fake_provider_secret: str = "local-dev-only"  # noqa: S105 — dev/test only; prod refuses the fake provider

    anthropic_api_key: str = ""
    anthropic_model_main: str = ""  # set in .env — never hardcoded in code
    anthropic_model_fast: str = ""

    @property
    def is_local(self) -> bool:
        """Dev/test only features (fake payment provider, skeleton adapters) are allowed only here."""
        return self.env in ("local", "test")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # values (incl. required ENV) come from the environment


settings = get_settings()
