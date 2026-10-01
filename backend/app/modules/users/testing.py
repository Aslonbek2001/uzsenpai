"""Factories other modules' TESTS may use to create users (never import users.models outside this module)."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.domain.enums import UserRole
from app.modules.users.models import User


async def create_user(
    session: AsyncSession, *, display_name: str = "Test User", role: UserRole = UserRole.USER
) -> uuid.UUID:
    user = User(display_name=display_name, role=role)
    session.add(user)
    await session.flush()
    return user.id


async def set_role(session: AsyncSession, user_id: uuid.UUID, role: UserRole) -> None:
    user = await session.get_one(User, user_id)
    user.role = role
    await session.flush()
