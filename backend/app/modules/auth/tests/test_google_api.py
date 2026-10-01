"""Google sign-in / linking with a fake Google (the real client is exercised against Google only in staging)."""

from collections.abc import Iterator
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.modules.auth.domain.exceptions import SignInFailed
from app.modules.auth.providers.google import GoogleProfile
from app.modules.auth.routers.cookies import REFRESH_COOKIE
from app.modules.auth.routers.deps import get_google
from app.modules.auth.tests.conftest import CapturingSender, bearer, sign_up


class FakeGoogle:
    def __init__(self) -> None:
        self.profile = GoogleProfile(sub="g-123", email="dilnoza@gmail.com", email_verified=True, name="Dilnoza")
        self.nonces: dict[str, str] = {}

    def authorization_url(self, *, state: str, code_challenge: str, nonce: str) -> str:
        self.nonces[state] = nonce
        return f"https://accounts.google.test/auth?state={state}&code_challenge={code_challenge}"

    async def exchange(self, *, code: str, code_verifier: str, nonce: str) -> GoogleProfile:
        if code != "good-code" or not code_verifier:
            raise SignInFailed("auth.sign_in_failed")
        return self.profile


@pytest.fixture
def google(app: FastAPI) -> Iterator[FakeGoogle]:
    fake = FakeGoogle()
    app.dependency_overrides[get_google] = lambda: fake
    yield fake


async def go_through_google(client: AsyncClient, start_path: str, headers: dict[str, str] | None = None) -> str:
    """Start → (user consents at Google) → callback. Returns the website URL the browser lands on."""
    start = await client.post(f"/api/v1/auth/google/{start_path}", headers=headers or {})
    assert start.status_code == 200, start.text
    state = parse_qs(urlparse(start.json()["authorization_url"]).query)["state"][0]
    r = await client.get("/api/v1/auth/google/callback", params={"code": "good-code", "state": state})
    assert r.status_code == 303
    return str(r.headers["location"])


async def test_sign_in_creates_account_sets_cookie_and_never_puts_tokens_in_urls(
    client: AsyncClient, google: FakeGoogle
) -> None:
    landing = await go_through_google(client, "start")

    assert landing.endswith("/auth/google/done?result=signed_in")
    assert client.cookies.get(REFRESH_COOKIE)
    tokens = (await client.post("/api/v1/auth/refresh")).json()  # how the website gets its access token
    me = (await client.get("/api/v1/users/me", headers=bearer(tokens))).json()
    assert me["display_name"] == "Dilnoza"


async def test_second_sign_in_reuses_the_account(client: AsyncClient, google: FakeGoogle) -> None:
    await go_through_google(client, "start")
    first = await client.get("/api/v1/users/me", headers=bearer((await client.post("/api/v1/auth/refresh")).json()))
    await go_through_google(client, "start")
    second = await client.get("/api/v1/users/me", headers=bearer((await client.post("/api/v1/auth/refresh")).json()))
    assert first.json()["id"] == second.json()["id"]


async def test_state_works_once_and_bad_codes_fail(client: AsyncClient, google: FakeGoogle) -> None:
    start = await client.post("/api/v1/auth/google/start")
    state = parse_qs(urlparse(start.json()["authorization_url"]).query)["state"][0]

    bad = await client.get("/api/v1/auth/google/callback", params={"code": "forged", "state": state})
    assert bad.headers["location"].endswith("error=auth.sign_in_failed")
    replay = await client.get("/api/v1/auth/google/callback", params={"code": "good-code", "state": state})
    assert replay.headers["location"].endswith("error=auth.sign_in_failed")  # state already consumed
    cancelled = await client.get("/api/v1/auth/google/callback", params={"error": "access_denied"})
    assert cancelled.headers["location"].endswith("error=auth.sign_in_cancelled")


async def test_email_of_a_password_account_is_not_merged_silently(
    client: AsyncClient, google: FakeGoogle, mailbox: CapturingSender
) -> None:
    await sign_up(client, mailbox, email="dilnoza@gmail.com")
    client.cookies.clear()
    landing = await go_through_google(client, "start")
    assert landing.endswith("error=auth.email_registered")
    assert client.cookies.get(REFRESH_COOKIE) is None


async def test_link_google_to_signed_in_account(
    client: AsyncClient, google: FakeGoogle, mailbox: CapturingSender
) -> None:
    tokens = await sign_up(client, mailbox, email="dilnoza@gmail.com")
    landing = await go_through_google(client, "link", headers=bearer(tokens))
    assert landing.endswith("result=linked")

    providers = [i["provider"] for i in (await client.get("/api/v1/auth/identities", headers=bearer(tokens))).json()]
    assert sorted(providers) == ["email", "google"]
    client.cookies.clear()
    await go_through_google(client, "start")  # Google now signs into the same account
    me = await client.get("/api/v1/users/me", headers=bearer((await client.post("/api/v1/auth/refresh")).json()))
    assert me.json()["display_name"] == "Aziz"


async def test_google_disabled_without_credentials(client: AsyncClient) -> None:
    r = await client.post("/api/v1/auth/google/start")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "auth.provider_unavailable"
