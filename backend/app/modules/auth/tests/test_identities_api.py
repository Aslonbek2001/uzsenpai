"""Linking Telegram / email to an account, listing and unlinking sign-in methods."""

from httpx import AsyncClient

from app.modules.auth.tests.conftest import CapturingSender, bearer, sign_up, telegram_widget_data


async def test_link_telegram_then_sign_in_with_it(client: AsyncClient, mailbox: CapturingSender) -> None:
    tokens = await sign_up(client, mailbox)
    r = await client.post("/api/v1/auth/link/telegram", json=telegram_widget_data(9001), headers=bearer(tokens))
    assert r.status_code == 204

    via_telegram = (await client.post("/api/v1/auth/telegram/login", json=telegram_widget_data(9001))).json()
    me = (await client.get("/api/v1/users/me", headers=bearer(via_telegram))).json()
    assert me["display_name"] == "Aziz"  # same account, not a new one


async def test_telegram_of_another_account_cannot_be_linked(client: AsyncClient, mailbox: CapturingSender) -> None:
    await client.post("/api/v1/auth/telegram/login", json=telegram_widget_data(9001))  # someone else's account
    tokens = await sign_up(client, mailbox)
    r = await client.post("/api/v1/auth/link/telegram", json=telegram_widget_data(9001), headers=bearer(tokens))
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "auth.identity_in_use"


async def test_link_email_with_code_then_sign_in_with_password(client: AsyncClient, mailbox: CapturingSender) -> None:
    tokens = (await client.post("/api/v1/auth/telegram/login", json=telegram_widget_data(9001))).json()
    r = await client.post("/api/v1/auth/link/email/start", json={"email": "Jasur@Example.uz"}, headers=bearer(tokens))
    assert r.status_code == 202
    r = await client.post(
        "/api/v1/auth/link/email/confirm",
        json={"email": "jasur@example.uz", "code": mailbox.last().code, "password": "Tokyo-2026!"},
        headers=bearer(tokens),
    )
    assert r.status_code == 204
    login = await client.post("/api/v1/auth/email/login", json={"email": "jasur@example.uz", "password": "Tokyo-2026!"})
    assert login.status_code == 200


async def test_unlink_keeps_at_least_one_sign_in_method(client: AsyncClient, mailbox: CapturingSender) -> None:
    tokens = await sign_up(client, mailbox)
    r = await client.delete("/api/v1/auth/identities/email", headers=bearer(tokens))
    assert r.status_code == 409 and r.json()["error"]["code"] == "auth.last_identity"

    await client.post("/api/v1/auth/link/telegram", json=telegram_widget_data(9001), headers=bearer(tokens))
    assert (await client.delete("/api/v1/auth/identities/email", headers=bearer(tokens))).status_code == 204
    providers = [i["provider"] for i in (await client.get("/api/v1/auth/identities", headers=bearer(tokens))).json()]
    assert providers == ["telegram"]
    r = await client.delete("/api/v1/auth/identities/google", headers=bearer(tokens))
    assert r.status_code == 404 and r.json()["error"]["code"] == "auth.identity_not_found"
