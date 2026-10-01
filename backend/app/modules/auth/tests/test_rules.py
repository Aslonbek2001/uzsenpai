"""Pure rules: access tokens, Telegram signature check, codes."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings
from app.modules.auth.domain.rules import new_verification_code, normalize_email
from app.modules.auth.providers.telegram import verify_login_widget
from app.modules.auth.services import decode_access_token, issue_access_token
from app.modules.users.public import UserRole


def test_access_token_round_trip() -> None:
    user_id, family_id = uuid.uuid4(), uuid.uuid4()
    token, expires_in = issue_access_token(user_id, UserRole.ADMIN, family_id)
    claims = decode_access_token(token)
    assert claims is not None
    assert (claims.user_id, claims.role, claims.family_id) == (user_id, UserRole.ADMIN, family_id)
    assert expires_in == 900


def test_access_token_rejects_expired_forged_and_alg_none() -> None:
    now = datetime.now(UTC)
    base = {"iss": "uzsenpai-api", "sub": str(uuid.uuid4()), "role": "user", "sid": str(uuid.uuid4()), "typ": "access"}
    expired = jwt.encode(
        base | {"iat": now - timedelta(hours=1), "exp": now - timedelta(minutes=1)}, settings.jwt_secret
    )
    forged = jwt.encode(base | {"iat": now, "exp": now + timedelta(minutes=5)}, "x" * 40)
    unsigned = jwt.encode(  # an attacker's unsigned token
        base | {"iat": now, "exp": now + timedelta(minutes=5)},
        None,  # type: ignore[arg-type]
        algorithm="none",
    )
    wrong_type = jwt.encode(
        base | {"typ": "refresh", "iat": now, "exp": now + timedelta(minutes=5)}, settings.jwt_secret
    )
    for token in (expired, forged, unsigned, wrong_type, "garbage"):
        assert decode_access_token(token) is None


def test_telegram_signature_needs_the_bot_token() -> None:
    fields = {"id": "1", "auth_date": "1700000000", "hash": "00"}
    assert not verify_login_widget(fields, bot_token="", now=1700000001, max_age=timedelta(days=1))
    assert not verify_login_widget(fields, bot_token="123:abc", now=1700000001, max_age=timedelta(days=1))


def test_codes_and_emails() -> None:
    codes = {new_verification_code() for _ in range(200)}
    assert all(len(c) == 6 and c.isdigit() for c in codes)
    assert len(codes) > 150  # random, not a counter
    assert normalize_email("  Aziz@Example.UZ ") == "aziz@example.uz"
