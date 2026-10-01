"""Account deletion: request (restorable for 30 days) → anonymize. No HTTP, no commit."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import bus
from app.modules.users.domain.enums import UserStatus
from app.modules.users.domain.events import UserDeleted, UserDeletionRequested
from app.modules.users.domain.exceptions import NotPendingDeletion, UserNotFound
from app.modules.users.domain.rules import (
    ANONYMIZE_BATCH,
    ANONYMIZED_DISPLAY_NAME,
    DEFAULT_TIMEZONE,
    DELETION_GRACE_DAYS,
)
from app.modules.users.models import User
from app.modules.users.repositories import UserRepository
from app.modules.users.schemas import MeOut


class DeletionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def request(self, user_id: uuid.UUID) -> MeOut:
        user = await self.users.get(user_id)
        if user is None or user.status == UserStatus.DELETED:
            raise UserNotFound("users.not_found")
        if user.status == UserStatus.ACTIVE:
            user.status = UserStatus.DELETION_REQUESTED
            user.deletion_requested_at = datetime.now(UTC)
            # durable: signing out every device must not be lost (auth reacts in the worker)
            bus.publish(self.session, UserDeletionRequested(user_id=user.id), durable=True)
        return MeOut.model_validate(await self.users.save(user))

    async def restore(self, user_id: uuid.UUID) -> MeOut:
        user = await self.users.get(user_id)
        if user is None or user.status != UserStatus.DELETION_REQUESTED:
            raise NotPendingDeletion("users.not_pending_deletion")
        user.status = UserStatus.ACTIVE
        user.deletion_requested_at = None
        return MeOut.model_validate(await self.users.save(user))

    async def anonymize_due(self, now: datetime | None = None) -> int:
        """Anonymize one batch of users whose grace period ended. Returns how many (0 = nothing left)."""
        cutoff = (now or datetime.now(UTC)) - timedelta(days=DELETION_GRACE_DAYS)
        due = await self.users.due_for_anonymization(cutoff, ANONYMIZE_BATCH)
        for user in due:
            _anonymize(user)
            bus.publish(self.session, UserDeleted(user_id=user.id), durable=True)
        await self.session.flush()
        return len(due)


def _anonymize(user: User) -> None:
    """Keep the row (payments/orders reference the id), drop everything that identifies the person."""
    user.display_name = ANONYMIZED_DISPLAY_NAME
    user.residence_country = None
    user.timezone = DEFAULT_TIMEZONE
    user.jlpt_level = None
    user.goal = None
    user.onboarding_completed_at = None
    user.status = UserStatus.DELETED
    user.deleted_at = datetime.now(UTC)
