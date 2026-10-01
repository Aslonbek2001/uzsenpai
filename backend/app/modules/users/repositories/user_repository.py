"""The only code that queries users_users."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

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
