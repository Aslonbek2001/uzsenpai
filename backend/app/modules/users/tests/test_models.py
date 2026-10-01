"""Database guarantees of users_users (constraints the services will rely on)."""

from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.domain.enums import UserRole, UserStatus
from app.modules.users.models import User
from app.shared.i18n import Locale


async def insert(session: AsyncSession, **fields: Any) -> User:
    user = User(display_name="Aziz", **fields)
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def test_defaults(db_session: AsyncSession) -> None:
    user = await insert(db_session)
    assert user.id.version == 7
    assert (user.locale, user.role, user.status) == (Locale.UZ, UserRole.USER, UserStatus.ACTIVE)
    assert user.timezone == "Asia/Tashkent"
    assert user.created_at is not None and user.updated_at is not None


@pytest.mark.parametrize(
    "fields",
    [
        {"residence_country": "jp"},  # must be ISO alpha-2 upper case
        {"residence_country": "JPN"},
        {"status": UserStatus.DELETION_REQUESTED},  # without deletion_requested_at
        {"deletion_requested_at": datetime.now(UTC)},  # timestamp while still active
        {"status": UserStatus.DELETED, "deletion_requested_at": datetime.now(UTC)},  # without deleted_at
    ],
)
async def test_rejects_inconsistent_rows(db_session: AsyncSession, fields: dict[str, Any]) -> None:
    with pytest.raises(DBAPIError):  # IntegrityError (constraints) or DataError (too long)
        async with db_session.begin_nested():
            await insert(db_session, **fields)


async def test_deleted_lifecycle_is_accepted(db_session: AsyncSession) -> None:
    now = datetime.now(UTC)
    user = await insert(db_session, status=UserStatus.DELETED, deletion_requested_at=now, deleted_at=now)
    assert user.status == UserStatus.DELETED
