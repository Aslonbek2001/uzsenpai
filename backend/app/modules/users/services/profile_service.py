"""Use cases for the user's own profile. No HTTP, no commit (the request owns the transaction)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.domain.enums import UserStatus
from app.modules.users.domain.exceptions import UserNotFound
from app.modules.users.models import User
from app.modules.users.repositories import UserRepository
from app.modules.users.schemas import MeOut, MeUpdateIn

# Fields that may be set to null by the client; display_name / locale / timezone can only be replaced.
_NULLABLE = {"residence_country", "jlpt_level", "goal"}


class ProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self.users = UserRepository(session)

    async def _active(self, user_id: uuid.UUID) -> User:
        user = await self.users.get(user_id)
        if user is None or user.status == UserStatus.DELETED:
            raise UserNotFound("users.not_found")
        return user

    async def get_me(self, user_id: uuid.UUID) -> MeOut:
        return MeOut.model_validate(await self._active(user_id))

    async def update_me(self, user_id: uuid.UUID, data: MeUpdateIn) -> MeOut:
        user = await self._active(user_id)
        changes = data.model_dump(exclude_unset=True)
        if changes.pop("onboarding_completed", None) and user.onboarding_completed_at is None:
            user.onboarding_completed_at = datetime.now(UTC)
        for field, value in changes.items():
            if value is None and field not in _NULLABLE:
                continue  # required fields can't be cleared
            setattr(user, field, value)
        return MeOut.model_validate(await self.users.save(user))
