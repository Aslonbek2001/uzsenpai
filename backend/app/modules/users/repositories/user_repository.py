"""The only code that queries users_users."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.domain.enums import UserStatus
from app.modules.users.models import User
from app.shared.i18n import Locale


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def add(self, display_name: str, locale: Locale) -> User:
        user = User(display_name=display_name, locale=locale)
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)  # load server defaults (timezone, created_at …)
        return user

    async def save(self, user: User) -> User:
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def due_for_anonymization(self, requested_before: datetime, limit: int) -> list[User]:
        """Locked with SKIP LOCKED so two job runs never anonymize the same user twice."""
        stmt = (
            select(User)
            .where(User.status == UserStatus.DELETION_REQUESTED, User.deletion_requested_at < requested_before)
            .order_by(User.deletion_requested_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(await self.session.scalars(stmt))
