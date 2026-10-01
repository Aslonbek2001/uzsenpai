import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.models import Grant


def _active(user_id: uuid.UUID, key: str, now: datetime) -> tuple[ColumnElement[bool], ...]:
    return (
        Grant.user_id == user_id,
        Grant.key == key,
        Grant.revoked_at.is_(None),
        or_(Grant.expires_at.is_(None), Grant.expires_at > now),
        or_(Grant.remaining.is_(None), Grant.remaining > 0),
    )


class GrantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, **fields: Any) -> None:
        self.session.add(Grant(**fields))

    async def active_keys(self, user_id: uuid.UUID, now: datetime) -> list[str]:
        stmt = (
            select(Grant.key)
            .where(
                Grant.user_id == user_id,
                Grant.revoked_at.is_(None),
                or_(Grant.expires_at.is_(None), Grant.expires_at > now),
                or_(Grant.remaining.is_(None), Grant.remaining > 0),
            )
            .distinct()
        )
        return list(await self.session.scalars(stmt))

    async def has_active(self, user_id: uuid.UUID, key: str, now: datetime) -> bool:
        return await self.session.scalar(select(Grant.id).where(*_active(user_id, key, now)).limit(1)) is not None

    async def has_unlimited(self, user_id: uuid.UUID, key: str, now: datetime) -> bool:
        stmt = select(Grant.id).where(*_active(user_id, key, now), Grant.remaining.is_(None)).limit(1)
        return await self.session.scalar(stmt) is not None

    async def decrement_one(self, user_id: uuid.UUID, key: str, now: datetime) -> bool:
        """Atomic: lock the soonest-expiring quota grant and decrement it only if still > 0."""
        target = (
            select(Grant.id)
            .where(*_active(user_id, key, now), Grant.remaining.is_not(None))
            .order_by(Grant.expires_at.asc().nulls_last())
            .limit(1)
            .with_for_update()
            .scalar_subquery()
        )
        stmt = (
            update(Grant)
            .where(Grant.id == target, Grant.remaining > 0)
            .values(remaining=Grant.remaining - 1, updated_at=now)
            .returning(Grant.id)
        )
        return await self.session.scalar(stmt) is not None
