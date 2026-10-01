"""Access checks for paid features. Quota is consumed only AFTER the paid action succeeded."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.domain.exceptions import NoEntitlement
from app.modules.billing.repositories import GrantRepository


class EntitlementService:
    def __init__(self, session: AsyncSession) -> None:
        self.grants = GrantRepository(session)

    async def keys(self, user_id: uuid.UUID) -> list[str]:
        return await self.grants.active_keys(user_id, datetime.now(UTC))

    async def has_access(self, user_id: uuid.UUID, key: str) -> bool:
        return await self.grants.has_active(user_id, key, datetime.now(UTC))

    async def consume(self, user_id: uuid.UUID, key: str) -> None:
        now = datetime.now(UTC)
        if await self.grants.has_unlimited(user_id, key, now):
            return
        if await self.grants.decrement_one(user_id, key, now):
            return
        # A concurrent request may have emptied the grant we waited on while another still has quota → retry once
        if await self.grants.decrement_one(user_id, key, now):
            return
        raise NoEntitlement("billing.no_entitlement", params={"key": key})
