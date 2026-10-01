"""Use cases for the user's residence status. No HTTP, no commit (the request owns the transaction)."""

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import bus
from app.modules.visa.domain.enums import ResidenceStatus
from app.modules.visa.domain.events import VisaStatusSaved
from app.modules.visa.domain.exceptions import VisaStatusNotSet
from app.modules.visa.domain.rules import ensure_future, urgency_for
from app.modules.visa.models import VisaStatus
from app.modules.visa.repositories import VisaStatusRepository
from app.modules.visa.schemas import VisaStatusIn, VisaStatusOut


def _to_out(row: VisaStatus, today: date) -> VisaStatusOut:
    days_left = (row.expires_on - today).days
    return VisaStatusOut(
        residence_status=ResidenceStatus(row.residence_status),
        expires_on=row.expires_on,
        days_left=days_left,
        urgency=urgency_for(days_left),
    )


class VisaStatusService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.statuses = VisaStatusRepository(session)

    async def get(self, user_id: uuid.UUID, today: date) -> VisaStatusOut:
        row = await self.statuses.get_for_user(user_id)
        if row is None:
            raise VisaStatusNotSet("visa.status_not_set")
        return _to_out(row, today)

    async def save(self, user_id: uuid.UUID, data: VisaStatusIn, today: date) -> VisaStatusOut:
        ensure_future(data.expires_on, today)
        row = await self.statuses.upsert(user_id, data.residence_status.value, data.expires_on)
        # Reminders must not be lost → durable (outbox), handled by notifications in the worker
        bus.publish(self.session, VisaStatusSaved(user_id=user_id, expires_on=row.expires_on), durable=True)
        return _to_out(row, today)
