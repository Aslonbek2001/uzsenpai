"""Sessions = refresh-token families. Start, rotate (with theft detection), sign out, list devices."""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from ipaddress import IPv4Address, IPv6Address

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.domain.enums import SessionRevokeReason
from app.modules.auth.domain.exceptions import AccountDeleted, InvalidRefreshToken, RefreshRace, SessionNotFound
from app.modules.auth.domain.rules import REFRESH_RACE_GRACE, REFRESH_TOKEN_TTL, hash_token, new_refresh_token
from app.modules.auth.repositories import SessionRepository
from app.modules.auth.schemas import SessionOut
from app.modules.auth.services.access_tokens import issue_access_token
from app.modules.users.public import UserDTO, UsersFacade
from app.shared.ids import uuid7

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClientInfo:
    user_agent: str | None
    ip: IPv4Address | IPv6Address | None


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    expires_in: int
    refresh_token: str  # goes ONLY into the httpOnly cookie
    refresh_expires_at: datetime


class SessionService:
    def __init__(self, session: AsyncSession) -> None:
        self.sessions = SessionRepository(session)
        self.users = UsersFacade(session)

    async def start(self, user: UserDTO, client: ClientInfo) -> IssuedTokens:
        """New sign-in → new family (one row in the "Devices" list)."""
        if not user.can_sign_in:
            raise AccountDeleted("auth.account_deleted")
        return await self._issue(user, uuid7(), client)

    async def refresh(self, refresh_token: str, client: ClientInfo) -> IssuedTokens | None:
        """New tokens, or None when the token was rejected AND sessions were revoked as a consequence.

        None (instead of raising) matters: an exception rolls the request transaction back, which would undo the
        revocation and let a thief keep the device. The router answers 401 for None without raising.
        """
        now = datetime.now(UTC)
        row = await self.sessions.get_by_hash_for_update(hash_token(refresh_token))
        if row is None:
            raise InvalidRefreshToken("auth.invalid_refresh")
        if row.revoked_at is not None:
            if row.revoke_reason == SessionRevokeReason.ROTATED:
                if now - row.revoked_at <= REFRESH_RACE_GRACE:
                    raise RefreshRace("auth.refresh_race")
                # A token replaced long ago is back: someone copied it. Sign the whole device out.
                await self.sessions.revoke_family(row.family_id, SessionRevokeReason.REUSE_DETECTED)
                log.warning("refresh token reuse detected", extra={"family_id": str(row.family_id)})
                return None
            raise InvalidRefreshToken("auth.invalid_refresh")
        if row.expires_at <= now:
            raise InvalidRefreshToken("auth.invalid_refresh")
        user = await self.users.get(row.user_id)
        if user is None or not user.can_sign_in:
            await self.sessions.revoke_family(row.family_id, SessionRevokeReason.ACCOUNT_DELETED)
            return None
        row.last_used_at = now
        await self.sessions.revoke(row, SessionRevokeReason.ROTATED, now)
        return await self._issue(user, row.family_id, client)

    async def logout(self, refresh_token: str) -> None:
        """Sign this device out. Unknown / already revoked tokens are fine (logout is idempotent)."""
        row = await self.sessions.get_by_hash_for_update(hash_token(refresh_token))
        if row is not None:
            await self.sessions.revoke_family(row.family_id, SessionRevokeReason.LOGOUT)

    async def logout_all(
        self, user_id: uuid.UUID, reason: SessionRevokeReason = SessionRevokeReason.LOGOUT_ALL
    ) -> None:
        await self.sessions.revoke_all_for_user(user_id, reason)

    async def revoke_device(self, user_id: uuid.UUID, family_id: uuid.UUID) -> None:
        if await self.sessions.family_owner(family_id) != user_id:
            raise SessionNotFound("auth.session_not_found")  # someone else's device looks like a missing one
        await self.sessions.revoke_family(family_id, SessionRevokeReason.LOGOUT)

    async def devices(self, user_id: uuid.UUID, current_family: uuid.UUID | None) -> list[SessionOut]:
        return [
            SessionOut(
                family_id=row.family_id,
                user_agent=row.user_agent,
                ip=str(row.ip) if row.ip is not None else None,
                last_active_at=row.created_at,  # the head row is created on every refresh
                expires_at=row.expires_at,
                current=row.family_id == current_family,
            )
            for row in await self.sessions.active_for_user(user_id)
        ]

    async def _issue(self, user: UserDTO, family_id: uuid.UUID, client: ClientInfo) -> IssuedTokens:
        refresh_token = new_refresh_token()
        expires_at = datetime.now(UTC) + REFRESH_TOKEN_TTL  # sliding: every refresh extends by 30 days
        await self.sessions.add(
            user_id=user.id,
            family_id=family_id,
            token_hash=hash_token(refresh_token),
            expires_at=expires_at,
            user_agent=client.user_agent[:500] if client.user_agent else None,
            ip=client.ip,
        )
        access_token, expires_in = issue_access_token(user.id, user.role, family_id)
        return IssuedTokens(access_token, expires_in, refresh_token, expires_at)
