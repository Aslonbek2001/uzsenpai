"""The only code that queries auth_sessions."""

import uuid
from datetime import datetime
from ipaddress import IPv4Address, IPv6Address

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.domain.enums import SessionRevokeReason
from app.modules.auth.models import Session


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self,
        *,
        user_id: uuid.UUID,
        family_id: uuid.UUID,
        token_hash: bytes,
        expires_at: datetime,
        user_agent: str | None,
        ip: IPv4Address | IPv6Address | None,
    ) -> Session:
        row = Session(
            user_id=user_id,
            family_id=family_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip=ip,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_by_hash_for_update(self, token_hash: bytes) -> Session | None:
        """Row-locks the token so two concurrent refreshes of the same token are serialized."""
        return await self.session.scalar(select(Session).where(Session.token_hash == token_hash).with_for_update())

    async def revoke(self, row: Session, reason: SessionRevokeReason, now: datetime) -> None:
        row.revoked_at = now
        row.revoke_reason = reason
        await self.session.flush()

    async def revoke_family(self, family_id: uuid.UUID, reason: SessionRevokeReason) -> int:
        result = await self.session.execute(
            update(Session)
            .where(Session.family_id == family_id, Session.revoked_at.is_(None))
            .values(revoked_at=func.now(), revoke_reason=reason)
        )
        return int(result.rowcount)  # type: ignore[attr-defined]

    async def revoke_all_for_user(self, user_id: uuid.UUID, reason: SessionRevokeReason) -> int:
        result = await self.session.execute(
            update(Session)
            .where(Session.user_id == user_id, Session.revoked_at.is_(None))
            .values(revoked_at=func.now(), revoke_reason=reason)
        )
        return int(result.rowcount)  # type: ignore[attr-defined]

    async def active_for_user(self, user_id: uuid.UUID) -> list[Session]:
        """Live head of every family (= one row per signed-in device), most recently used first."""
        stmt = (
            select(Session)
            .where(Session.user_id == user_id, Session.revoked_at.is_(None), Session.expires_at > func.now())
            .order_by(Session.created_at.desc())
        )
        return list(await self.session.scalars(stmt))

    async def family_owner(self, family_id: uuid.UUID) -> uuid.UUID | None:
        return await self.session.scalar(select(Session.user_id).where(Session.family_id == family_id).limit(1))
