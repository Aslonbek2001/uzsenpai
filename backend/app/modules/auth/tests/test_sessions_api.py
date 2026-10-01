"""Refresh rotation, theft detection, sign-out and the "Devices" list."""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Session
from app.modules.auth.routers.cookies import REFRESH_COOKIE
from app.modules.auth.tests.conftest import CapturingSender, bearer, sign_up

REFRESH = "/api/v1/auth/refresh"


async def test_refresh_rotates_the_cookie(client: AsyncClient, mailbox: CapturingSender) -> None:
    await sign_up(client, mailbox)
    first = client.cookies.get(REFRESH_COOKIE)

    r = await client.post(REFRESH)

    assert r.status_code == 200
    assert r.json()["access_token"]
    assert client.cookies.get(REFRESH_COOKIE) not in (None, first)


async def test_without_cookie_refresh_is_unauthorized(client: AsyncClient) -> None:
    r = await client.post(REFRESH)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "auth.invalid_refresh"


async def test_concurrent_tab_gets_a_retryable_race_not_a_logout(client: AsyncClient, mailbox: CapturingSender) -> None:
    await sign_up(client, mailbox)
    old = client.cookies.get(REFRESH_COOKIE)
    await client.post(REFRESH)  # tab A wins
    new = client.cookies.get(REFRESH_COOKIE)

    client.cookies.set(REFRESH_COOKIE, old or "", path="/api/v1/auth")  # tab B still holds the old token
    r = await client.post(REFRESH)
    assert r.status_code == 409 and r.json()["error"]["code"] == "auth.refresh_race"

    client.cookies.set(REFRESH_COOKIE, new or "", path="/api/v1/auth")  # B retries with the shared new cookie
    assert (await client.post(REFRESH)).status_code == 200


async def test_reused_old_token_revokes_the_whole_device(
    client: AsyncClient, mailbox: CapturingSender, db_session: AsyncSession
) -> None:
    await sign_up(client, mailbox)
    stolen = client.cookies.get(REFRESH_COOKIE)
    await client.post(REFRESH)
    legit = client.cookies.get(REFRESH_COOKIE)
    # the stolen token was rotated long ago (outside the race window)
    await db_session.execute(
        update(Session)
        .where(Session.revoke_reason == "rotated")
        .values(revoked_at=datetime.now(UTC) - timedelta(minutes=5))
    )

    client.cookies.set(REFRESH_COOKIE, stolen or "", path="/api/v1/auth")
    assert (await client.post(REFRESH)).status_code == 401
    client.cookies.set(REFRESH_COOKIE, legit or "", path="/api/v1/auth")
    assert (await client.post(REFRESH)).status_code == 401  # the thief's reuse signed the device out


async def test_logout_clears_cookie_and_kills_refresh(client: AsyncClient, mailbox: CapturingSender) -> None:
    await sign_up(client, mailbox)
    token = client.cookies.get(REFRESH_COOKIE)

    r = await client.post("/api/v1/auth/logout")
    assert r.status_code == 204
    assert 'uzs_refresh=""' in r.headers["set-cookie"] or "Max-Age=0" in r.headers["set-cookie"]

    client.cookies.set(REFRESH_COOKIE, token or "", path="/api/v1/auth")
    assert (await client.post(REFRESH)).status_code == 401


async def test_devices_list_and_revoking_another_device(client: AsyncClient, mailbox: CapturingSender) -> None:
    phone = await sign_up(client, mailbox)
    laptop = (
        await client.post("/api/v1/auth/email/login", json={"email": "aziz@example.uz", "password": "Sakura-2026!"})
    ).json()

    r = await client.get("/api/v1/auth/sessions", headers=bearer(laptop))
    devices = r.json()
    assert len(devices) == 2
    assert sum(d["current"] for d in devices) == 1
    phone_family = next(d["family_id"] for d in devices if not d["current"])

    assert (await client.delete(f"/api/v1/auth/sessions/{phone_family}", headers=bearer(laptop))).status_code == 204
    remaining = (await client.get("/api/v1/auth/sessions", headers=bearer(phone))).json()
    assert [d["current"] for d in remaining] == [False]  # only the laptop is left


async def test_cannot_revoke_someone_elses_device(client: AsyncClient, mailbox: CapturingSender) -> None:
    mine = await sign_up(client, mailbox, email="me@example.uz")
    other = await sign_up(client, mailbox, email="other@example.uz")
    other_family = (await client.get("/api/v1/auth/sessions", headers=bearer(other))).json()[0]["family_id"]

    r = await client.delete(f"/api/v1/auth/sessions/{other_family}", headers=bearer(mine))
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "auth.session_not_found"


async def test_logout_all(client: AsyncClient, mailbox: CapturingSender) -> None:
    tokens = await sign_up(client, mailbox)
    assert (await client.post("/api/v1/auth/logout-all", headers=bearer(tokens))).status_code == 204
    assert (await client.get("/api/v1/auth/sessions", headers=bearer(tokens))).json() == []
