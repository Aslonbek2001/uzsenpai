"""bot/app/services/api_client.py — the bot's only door to data."""
from typing import Any

import httpx
from pydantic import BaseModel


class BotUser(BaseModel):
    id: str
    locale: str
    language_confirmed: bool


class BackendError(Exception):
    def __init__(self, code: str, status: int, params: dict[str, Any] | None = None) -> None:
        super().__init__(code)
        self.code, self.status, self.params = code, status, params or {}


class BackendClient:
    def __init__(self, base_url: str, service_token: str) -> None:
        self._http = httpx.AsyncClient(
            base_url=f"{base_url}/api/v1",
            headers={"Authorization": f"Bearer {service_token}"},
            timeout=httpx.Timeout(10.0, read=30.0),
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            r = await self._http.request(method, path, **kwargs)
        except httpx.HTTPError as e:  # backend down, timeout, connection reset
            raise BackendError("common.unavailable", 503) from e
        if r.is_error:
            body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            err = body.get("error", {})
            raise BackendError(err.get("code", "common.unknown"), r.status_code, err.get("params"))
        return r.json() if r.content else None

    async def get_or_create_telegram_user(self, telegram_id: int, first_name: str, locale_hint: str) -> BotUser:
        data = await self._request(
            "POST", "/auth/bot/users", json={"telegram_id": telegram_id, "first_name": first_name, "locale_hint": locale_hint}
        )
        return BotUser.model_validate(data)

    async def update_locale(self, telegram_id: int, locale: str) -> None:
        # The bot acts for the user: service token (client default header) + X-Telegram-User-Id
        await self._request(
            "PATCH", "/users/me", json={"locale": locale}, headers={"X-Telegram-User-Id": str(telegram_id)}
        )

    async def list_products(self, locale: str, currency: str = "UZS") -> list[dict[str, Any]]:
        # Prices and texts come localized from the backend (GET /api/v1/catalog/products) — never hardcoded
        result: list[dict[str, Any]] = await self._request(
            "GET", "/catalog/products", params={"currency": currency}, headers={"Accept-Language": locale}
        )
        return result
