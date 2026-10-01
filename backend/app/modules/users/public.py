"""The ONLY surface other modules may import from `users`: a facade + DTOs (never ORM objects)."""

import uuid

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.domain.enums import UserRole, UserStatus
from app.modules.users.repositories import UserRepository
from app.shared.i18n import Locale


class UserDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: uuid.UUID
    display_name: str
    locale: Locale
    role: UserRole
    status: UserStatus

    @property
    def can_sign_in(self) -> bool:
        """Deleted (anonymized) users can't sign in; a pending deletion is cancelled by signing in (2b)."""
        return self.status != UserStatus.DELETED


class UsersFacade:
    """Takes the caller's session so cross-module work stays in one transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._users = UserRepository(session)

    async def create(self, *, display_name: str, locale: Locale) -> UserDTO:
        return UserDTO.model_validate(await self._users.add(display_name.strip()[:100] or "User", locale))

    async def get(self, user_id: uuid.UUID) -> UserDTO | None:
        user = await self._users.get(user_id)
        return None if user is None else UserDTO.model_validate(user)


__all__ = ["UserDTO", "UserRole", "UserStatus", "UsersFacade"]
