"""The only code that queries visa_statuses."""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.visa.models import VisaStatus


class VisaStatusRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_for_user(self, user_id: uuid.UUID) -> VisaStatus | None:
        return await self.session.scalar(select(VisaStatus).where(VisaStatus.user_id == user_id))

    async def upsert(self, user_id: uuid.UUID, residence_status: str, expires_on: date) -> VisaStatus:
        row = await self.get_for_user(user_id)
        if row is None:
            row = VisaStatus(user_id=user_id, residence_status=residence_status, expires_on=expires_on)
            self.session.add(row)
        else:
            row.residence_status = residence_status
            row.expires_on = expires_on
        await self.session.flush()
        return row

    async def expiring_between(self, start: date, end: date, *, limit: int = 500) -> list[VisaStatus]:
        stmt = (
            select(VisaStatus)
            .where(VisaStatus.expires_on >= start, VisaStatus.expires_on <= end)
            .order_by(VisaStatus.expires_on)
            .limit(limit)
        )
        return list(await self.session.scalars(stmt))
