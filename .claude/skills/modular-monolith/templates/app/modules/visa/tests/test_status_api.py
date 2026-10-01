"""Integration tests: real app, real DB (rolled back per test), fake auth via fixtures in tests/conftest.py."""

from datetime import date

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.outbox import OutboxMessage
from app.modules.visa.routers.deps import today

pytestmark = pytest.mark.asyncio


async def test_save_and_get_status(client: AsyncClient, auth_headers: dict[str, str], app: FastAPI) -> None:
    app.dependency_overrides[today] = lambda: date(2026, 10, 1)
    r = await client.put(
        "/api/v1/visa/status",
        json={"residence_status": "tokutei_gino_1", "expires_on": "2026-12-26"},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["days_left"] == 86
    assert r.json()["urgency"] == "soon"

    r = await client.get("/api/v1/visa/status", headers=auth_headers)
    assert r.json()["expires_on"] == "2026-12-26"


async def test_expiry_in_past_returns_code(client: AsyncClient, auth_headers: dict[str, str], app: FastAPI) -> None:
    app.dependency_overrides[today] = lambda: date(2026, 10, 1)
    r = await client.put(
        "/api/v1/visa/status",
        json={"residence_status": "student", "expires_on": "2026-01-01"},
        headers=auth_headers,
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "visa.expiry_in_past"  # a code, never a sentence


async def test_status_not_set_is_404_code(client: AsyncClient, other_user_headers: dict[str, str]) -> None:
    r = await client.get("/api/v1/visa/status", headers=other_user_headers)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "visa.status_not_set"


async def test_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/api/v1/visa/status")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "common.unauthorized"


async def test_saving_writes_durable_reminder_event(
    client: AsyncClient, auth_headers: dict[str, str], app: FastAPI, db_session: AsyncSession
) -> None:
    app.dependency_overrides[today] = lambda: date(2026, 10, 1)
    await client.put(
        "/api/v1/visa/status",
        json={"residence_status": "gijinkoku", "expires_on": "2027-03-01"},
        headers=auth_headers,
    )
    names = (await db_session.scalars(select(OutboxMessage.name))).all()
    assert names == ["VisaStatusSaved"]  # same transaction as the change → reminders can't be lost
