"""The ONLY surface other modules may import from `visa`: a facade + DTOs (never ORM objects)."""

import uuid
from datetime import date

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.visa.domain.events import VisaStatusSaved
from app.modules.visa.repositories import VisaStatusRepository


class ExpiringVisaDTO(BaseModel):
    user_id: uuid.UUID
    residence_status: str
    expires_on: date


class VisaFacade:
    """Takes the caller's session so cross-module work stays in one transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._statuses = VisaStatusRepository(session)

    async def expiring_between(self, start: date, end: date) -> list[ExpiringVisaDTO]:
        rows = await self._statuses.expiring_between(start, end)
        return [
            ExpiringVisaDTO(user_id=r.user_id, residence_status=r.residence_status, expires_on=r.expires_on)
            for r in rows
        ]


__all__ = ["ExpiringVisaDTO", "VisaFacade", "VisaStatusSaved"]
