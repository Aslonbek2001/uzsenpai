"""Telegram Login Widget, the bot's user resolution, and the bot acting for a user."""

import time
import uuid

from fastapi import Depends, FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.auth.public import require_admin
from app.modules.auth.testing import auth_headers_for
from app.modules.auth.tests.conftest import bearer, telegram_widget_data
from app.modules.users.public import UserRole
from app.modules.users.testing import set_role

BOT = {"Authorization": f"Bearer {settings.bot_service_token}"}


async def test_widget_sign_in_creates_once_then_reuses_the_user(client: AsyncClient) -> None:
    first = await client.post("/api/v1/auth/telegram/login", json=telegram_widget_data(777))
    second = await client.post("/api/v1/auth/telegram/login", json=telegram_widget_data(777))
    assert first.status_code == second.status_code == 200

    me1 = (await client.get("/api/v1/users/me", headers=bearer(first.json()))).json()
    me2 = (await client.get("/api/v1/users/me", headers=bearer(second.json()))).json()
    assert me1["id"] == me2["id"]
    assert me1["display_name"] == "Dilnoza"


async def test_widget_rejects_tampered_or_stale_data(client: AsyncClient) -> None:
    tampered = telegram_widget_data(777) | {"id": 778}
    stale = telegram_widget_data(777, auth_date=int(time.time()) - 11 * 60)  # older than 10 minutes
    for data in (tampered, stale):
        r = await client.post("/api/v1/auth/telegram/login", json=data)
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "auth.invalid_telegram_data"


async def test_bot_resolves_users_and_acts_for_them(client: AsyncClient) -> None:
    payload = {"telegram_id": 555, "first_name": "Jasur", "locale_hint": "ru"}
    created = await client.post("/api/v1/auth/bot/users", json=payload, headers=BOT)
    again = await client.post("/api/v1/auth/bot/users", json=payload, headers=BOT)
    assert created.json()["created"] is True and again.json()["created"] is False
    assert created.json()["user_id"] == again.json()["user_id"]
    assert created.json()["locale"] == "ru"

    me = await client.get("/api/v1/users/me", headers=BOT | {"X-Telegram-User-Id": "555"})
    assert me.status_code == 200 and me.json()["id"] == created.json()["user_id"]


async def test_bot_endpoints_need_the_service_token(client: AsyncClient) -> None:
    r = await client.post("/api/v1/auth/bot/users", json={"telegram_id": 1, "first_name": "X"})
    assert r.status_code == 401
    r = await client.post(
        "/api/v1/auth/bot/users", json={"telegram_id": 1, "first_name": "X"}, headers={"Authorization": "Bearer nope"}
    )
    assert r.status_code == 401


async def test_bot_cannot_act_for_an_unknown_telegram_user(client: AsyncClient) -> None:
    r = await client.get("/api/v1/users/me", headers=BOT | {"X-Telegram-User-Id": "999999"})
    assert r.status_code == 401
    r = await client.get("/api/v1/users/me", headers=BOT)  # header missing
    assert r.status_code == 401


async def test_bot_never_gets_admin_rights(client: AsyncClient, app: FastAPI, db_session: AsyncSession) -> None:
    """A leaked bot token must not become an admin takeover, even when acting for a real admin."""
    app.add_api_route("/test-only/admin", lambda: {"ok": True}, dependencies=[Depends(require_admin)])
    created = await client.post("/api/v1/auth/bot/users", json={"telegram_id": 42, "first_name": "Boss"}, headers=BOT)
    admin_id = uuid.UUID(created.json()["user_id"])
    await set_role(db_session, admin_id, UserRole.ADMIN)

    via_bot = await client.get("/test-only/admin", headers=BOT | {"X-Telegram-User-Id": "42"})
    via_own_login = await client.get("/test-only/admin", headers=auth_headers_for(admin_id, UserRole.ADMIN))
    assert via_bot.status_code == 403
    assert via_own_login.status_code == 200
