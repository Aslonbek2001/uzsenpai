"""The ONLY surface other modules may import from `auth`: who is calling (`current_user`) and role guards.

Access tokens are verified without a database call, so sign-out, password reset or a role change take effect for
already-issued access tokens when they expire (≤ 15 minutes). Refresh is refused immediately.
"""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.db import SessionDep
from app.modules.auth.domain.enums import AuthProvider
from app.modules.auth.repositories import IdentityRepository
from app.modules.auth.services import decode_access_token, is_bot_token
from app.modules.users.public import UserRole, UsersFacade
from app.shared.errors import Forbidden

TELEGRAM_USER_HEADER = "X-Telegram-User-Id"

_bearer = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    id: uuid.UUID
    role: UserRole
    session_family_id: uuid.UUID | None = None  # None when the bot acts for the user


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=401, headers={"WWW-Authenticate": "Bearer"})


async def current_user(
    request: Request,
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> CurrentUser:
    """Website/app: `Authorization: Bearer <access JWT>`.
    Bot: `Authorization: Bearer <BOT_SERVICE_TOKEN>` + `X-Telegram-User-Id: <id>` (the bot acts for that user)."""
    if credentials is None:
        raise _unauthorized()
    if is_bot_token(credentials.credentials):
        return await _user_behind_bot(request, session)
    claims = decode_access_token(credentials.credentials)
    if claims is None:
        raise _unauthorized()
    return CurrentUser(id=claims.user_id, role=claims.role, session_family_id=claims.family_id)


async def _user_behind_bot(request: Request, session: SessionDep) -> CurrentUser:
    telegram_id = request.headers.get(TELEGRAM_USER_HEADER, "")
    if not telegram_id.isdigit():
        raise _unauthorized()
    identity = await IdentityRepository(session).get(AuthProvider.TELEGRAM, telegram_id)
    user = await UsersFacade(session).get(identity.user_id) if identity else None
    if user is None or not user.can_sign_in:
        raise _unauthorized()  # the bot must resolve the user via /auth/bot/users first
    # Capped at USER: a leaked bot token must never grant admin rights
    return CurrentUser(id=user.id, role=UserRole.USER)


CurrentUserDep = Annotated[CurrentUser, Depends(current_user)]


async def require_admin(user: CurrentUserDep) -> CurrentUser:
    if user.role != UserRole.ADMIN:
        raise Forbidden("common.forbidden")
    return user


AdminDep = Annotated[CurrentUser, Depends(require_admin)]

__all__ = ["AdminDep", "CurrentUser", "CurrentUserDep", "current_user", "require_admin"]
