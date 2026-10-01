"""The only code that queries auth_identities."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.domain.enums import AuthProvider
from app.modules.auth.models import Identity


class IdentityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, provider: AuthProvider, subject: str) -> Identity | None:
        return await self.session.scalar(
            select(Identity).where(Identity.provider == provider, Identity.subject == subject)
        )

    async def add(
        self,
        *,
        user_id: uuid.UUID,
        provider: AuthProvider,
        subject: str,
        email: str | None = None,
        password_hash: str | None = None,
    ) -> Identity:
        now = datetime.now(UTC)
        identity = Identity(
            user_id=user_id,
            provider=provider,
            subject=subject,
            email=email,
            password_hash=password_hash,
            verified_at=now,  # every identity is created only after its owner proved it
            last_login_at=now,
        )
        self.session.add(identity)
        await self.session.flush()
        return identity

    async def touch_login(self, identity: Identity) -> None:
        identity.last_login_at = datetime.now(UTC)
        await self.session.flush()

    async def set_password(self, identity: Identity, password_hash: str) -> None:
        identity.password_hash = password_hash
        await self.session.flush()
