"""Database guarantees of auth_identities and auth_sessions."""

import hashlib
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.domain.enums import AuthProvider, SessionRevokeReason
from app.modules.auth.models import Identity, Session
from app.modules.users.testing import create_user


async def add(session: AsyncSession, row: Identity | Session) -> None:
    session.add(row)
    await session.flush()


async def assert_rejected(session: AsyncSession, row: Identity | Session) -> None:
    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            await add(session, row)


def refresh_session(user_id: uuid.UUID, **fields: Any) -> Session:
    defaults: dict[str, Any] = {
        "family_id": uuid.uuid4(),
        "token_hash": hashlib.sha256(os.urandom(32)).digest(),
        "expires_at": datetime.now(UTC) + timedelta(days=30),
    }
    return Session(user_id=user_id, **(defaults | fields))


async def test_user_links_one_identity_per_provider(db_session: AsyncSession) -> None:
    user_id = await create_user(db_session)
    await add(db_session, Identity(user_id=user_id, provider=AuthProvider.TELEGRAM, subject="1001"))
    await add(db_session, Identity(user_id=user_id, provider=AuthProvider.EMAIL, subject="a@b.uz", password_hash="h"))
    await add(db_session, Identity(user_id=user_id, provider=AuthProvider.GOOGLE, subject="g-1", email="a@b.uz"))

    await assert_rejected(db_session, Identity(user_id=user_id, provider=AuthProvider.TELEGRAM, subject="1002"))


async def test_same_login_cannot_belong_to_two_users(db_session: AsyncSession) -> None:
    first, second = await create_user(db_session), await create_user(db_session)
    await add(db_session, Identity(user_id=first, provider=AuthProvider.TELEGRAM, subject="1001"))
    await assert_rejected(db_session, Identity(user_id=second, provider=AuthProvider.TELEGRAM, subject="1001"))


async def test_password_only_on_email_and_email_lowercase(db_session: AsyncSession) -> None:
    user_id = await create_user(db_session)
    await assert_rejected(
        db_session, Identity(user_id=user_id, provider=AuthProvider.TELEGRAM, subject="1", password_hash="h")
    )
    await assert_rejected(db_session, Identity(user_id=user_id, provider=AuthProvider.EMAIL, subject="Aziz@B.uz"))


async def test_identity_requires_existing_user(db_session: AsyncSession) -> None:
    await assert_rejected(db_session, Identity(user_id=uuid.uuid4(), provider=AuthProvider.TELEGRAM, subject="1"))


async def test_session_revocation_needs_a_reason(db_session: AsyncSession) -> None:
    user_id = await create_user(db_session)
    await add(db_session, refresh_session(user_id))
    await add(
        db_session,
        refresh_session(user_id, revoked_at=datetime.now(UTC), revoke_reason=SessionRevokeReason.ROTATED),
    )
    await assert_rejected(db_session, refresh_session(user_id, revoked_at=datetime.now(UTC)))
    await assert_rejected(db_session, refresh_session(user_id, revoke_reason=SessionRevokeReason.LOGOUT))


async def test_session_token_hash_is_unique_and_ip_round_trips(db_session: AsyncSession) -> None:
    user_id = await create_user(db_session)
    first = refresh_session(user_id, ip="203.0.113.7")
    await add(db_session, first)
    await assert_rejected(db_session, refresh_session(user_id, token_hash=first.token_hash))
    stored = await db_session.scalar(select(Session.ip).where(Session.id == first.id))
    assert str(stored) == "203.0.113.7"
