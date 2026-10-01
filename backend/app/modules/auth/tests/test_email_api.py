"""Email + password: sign-up with a code, sign-in, password reset — through the real HTTP API."""

from typing import Any

from httpx import AsyncClient

from app.modules.auth.domain.enums import CodePurpose
from app.modules.auth.tests.conftest import CapturingSender, bearer, sign_up

REGISTER = "/api/v1/auth/email/register"
VERIFY = "/api/v1/auth/email/verify"
LOGIN = "/api/v1/auth/email/login"


def verify_body(email: str, code: str, password: str = "Sakura-2026!") -> dict[str, Any]:
    return {"email": email, "code": code, "password": password, "display_name": "Aziz"}


async def test_sign_up_creates_account_and_signs_in(client: AsyncClient, mailbox: CapturingSender) -> None:
    tokens = await sign_up(client, mailbox, email="Aziz@Example.UZ")

    assert mailbox.last().email == "aziz@example.uz"  # normalized
    assert mailbox.last().purpose == CodePurpose.SIGNUP
    assert tokens["token_type"] == "bearer" and tokens["expires_in"] == 900
    me = await client.get("/api/v1/users/me", headers=bearer(tokens))
    assert me.status_code == 200
    assert me.json()["display_name"] == "Aziz"


async def test_refresh_cookie_is_http_only_and_scoped(client: AsyncClient, mailbox: CapturingSender) -> None:
    await client.post(REGISTER, json={"email": "a@b.uz"})
    r = await client.post(VERIFY, json=verify_body("a@b.uz", mailbox.last().code))
    cookie = r.headers["set-cookie"]
    assert "uzs_refresh=" in cookie
    assert "HttpOnly" in cookie and "Path=/api/v1/auth" in cookie and "SameSite=lax" in cookie
    assert "refresh" not in r.json()  # never in the body


async def test_existing_email_gets_the_same_answer_but_no_code(client: AsyncClient, mailbox: CapturingSender) -> None:
    await sign_up(client, mailbox)
    sent_before = len(mailbox.sent)
    r = await client.post(REGISTER, json={"email": "aziz@example.uz"})
    assert r.status_code == 202
    assert len(mailbox.sent) == sent_before


async def test_only_the_mailbox_owner_sets_the_password(client: AsyncClient, mailbox: CapturingSender) -> None:
    """An attacker's sign-up request (before OR after the victim's) only triggers a code to the victim's
    mailbox; the password is chosen by whoever redeems the code — the victim."""
    email = "victim@example.uz"
    await client.post(REGISTER, json={"email": email})  # victim
    await client.post(REGISTER, json={"email": email})  # attacker, later — replaces the pending code
    victim_code = mailbox.last().code  # delivered to the victim's mailbox

    assert (await client.post(VERIFY, json=verify_body(email, victim_code, "Victim-pass-1"))).status_code == 200
    assert (await client.post(LOGIN, json={"email": email, "password": "Victim-pass-1"})).status_code == 200


async def test_only_the_latest_code_works(client: AsyncClient, mailbox: CapturingSender) -> None:
    await client.post(REGISTER, json={"email": "a@b.uz"})
    first = mailbox.last().code
    await client.post(REGISTER, json={"email": "a@b.uz"})
    second = mailbox.last().code
    if first != second:  # (1 in a million they collide)
        r = await client.post(VERIFY, json=verify_body("a@b.uz", first))
        assert r.json()["error"]["code"] == "auth.invalid_code"
    assert (await client.post(VERIFY, json=verify_body("a@b.uz", second))).status_code == 200


async def test_code_is_single_use_and_dies_after_five_wrong_attempts(
    client: AsyncClient, mailbox: CapturingSender
) -> None:
    await client.post(REGISTER, json={"email": "a@b.uz"})
    code = mailbox.last().code
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        r = await client.post(VERIFY, json=verify_body("a@b.uz", wrong))
        assert r.status_code == 400 and r.json()["error"]["code"] == "auth.invalid_code"
    r = await client.post(VERIFY, json=verify_body("a@b.uz", code))
    assert r.json()["error"]["code"] == "auth.invalid_code"  # burned


async def test_wrong_codes_per_email_are_capped_per_day(client: AsyncClient, mailbox: CapturingSender) -> None:
    for _ in range(20):
        await client.post(VERIFY, json=verify_body("a@b.uz", "123456"))
    await client.post(REGISTER, json={"email": "a@b.uz"})
    r = await client.post(VERIFY, json=verify_body("a@b.uz", mailbox.last().code))
    assert r.status_code == 429  # even the right code: this email's codes are locked for the day


async def test_login_errors_do_not_reveal_whether_the_email_exists(
    client: AsyncClient, mailbox: CapturingSender
) -> None:
    await sign_up(client, mailbox)
    wrong_password = await client.post(LOGIN, json={"email": "aziz@example.uz", "password": "nope-nope"})
    unknown_email = await client.post(LOGIN, json={"email": "nobody@example.uz", "password": "nope-nope"})
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert (
        wrong_password.json() == unknown_email.json() == {"error": {"code": "auth.invalid_credentials", "params": {}}}
    )


async def test_login_locks_after_ten_failures_but_successes_never_count(
    client: AsyncClient, mailbox: CapturingSender
) -> None:
    await sign_up(client, mailbox)
    good = {"email": "aziz@example.uz", "password": "Sakura-2026!"}
    for _ in range(12):
        assert (await client.post(LOGIN, json=good)).status_code == 200
    for _ in range(10):
        await client.post(LOGIN, json={"email": "aziz@example.uz", "password": "wrong-guess"})
    r = await client.post(LOGIN, json=good)
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "common.rate_limited"
    assert r.json()["error"]["params"]["retry_after"] > 0


async def test_password_reset_changes_password_and_signs_out_everywhere(
    client: AsyncClient, mailbox: CapturingSender
) -> None:
    await sign_up(client, mailbox)
    r = await client.post("/api/v1/auth/email/password/forgot", json={"email": "aziz@example.uz"})
    assert r.status_code == 202
    code = mailbox.last()
    assert code.purpose == CodePurpose.PASSWORD_RESET

    r = await client.post(
        "/api/v1/auth/email/password/reset",
        json={"email": "aziz@example.uz", "code": code.code, "new_password": "Fuji-san-3776"},
    )
    assert r.status_code == 204
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401  # old device signed out
    assert (await client.post(LOGIN, json={"email": "aziz@example.uz", "password": "Sakura-2026!"})).status_code == 401
    assert (await client.post(LOGIN, json={"email": "aziz@example.uz", "password": "Fuji-san-3776"})).status_code == 200


async def test_forgot_password_for_unknown_email_looks_the_same(client: AsyncClient, mailbox: CapturingSender) -> None:
    r = await client.post("/api/v1/auth/email/password/forgot", json={"email": "ghost@example.uz"})
    assert r.status_code == 202
    assert mailbox.sent == []


async def test_weak_password_is_a_validation_code(client: AsyncClient, mailbox: CapturingSender) -> None:
    await client.post(REGISTER, json={"email": "a@b.uz"})
    r = await client.post(VERIFY, json=verify_body("a@b.uz", mailbox.last().code, password="short"))
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "common.validation"
