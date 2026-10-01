"""Auth test fixtures: captured email codes and small HTTP helpers."""

import hashlib
import hmac
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.core.config import settings
from app.modules.auth.domain.enums import CodePurpose
from app.modules.auth.routers.deps import get_code_sender
from app.shared.i18n import Locale


@dataclass
class SentCode:
    email: str
    code: str
    purpose: CodePurpose
    locale: Locale


class CapturingSender:
    def __init__(self) -> None:
        self.sent: list[SentCode] = []

    async def send(self, *, email: str, code: str, purpose: CodePurpose, locale: Locale) -> None:
        self.sent.append(SentCode(email, code, purpose, locale))

    def last(self) -> SentCode:
        return self.sent[-1]


@pytest.fixture
def mailbox(app: FastAPI) -> Iterator[CapturingSender]:
    sender = CapturingSender()
    app.dependency_overrides[get_code_sender] = lambda: sender
    yield sender


async def sign_up(
    client: AsyncClient, mailbox: CapturingSender, email: str = "aziz@example.uz", password: str = "Sakura-2026!"
) -> dict[str, Any]:
    r = await client.post("/api/v1/auth/email/register", json={"email": email})
    assert r.status_code == 202, r.text
    r = await client.post(
        "/api/v1/auth/email/verify",
        json={"email": email, "code": mailbox.last().code, "password": password, "display_name": "Aziz"},
    )
    assert r.status_code == 200, r.text
    body: dict[str, Any] = r.json()
    return body


def bearer(token_body: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_body['access_token']}"}


def telegram_widget_data(telegram_id: int = 777, auth_date: int | None = None, **extra: Any) -> dict[str, Any]:
    """Signs fields exactly like Telegram does, with the test bot token."""
    fields: dict[str, Any] = {"id": telegram_id, "first_name": "Dilnoza", "auth_date": auth_date or int(time.time())}
    fields |= extra
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hashlib.sha256(settings.telegram_bot_token.encode()).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return fields
