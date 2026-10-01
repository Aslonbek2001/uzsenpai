"""Durable reactions to the users module's account lifecycle (run in the worker via the outbox)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.domain.enums import SessionRevokeReason
from app.modules.auth.repositories import IdentityRepository, SessionRepository
from app.modules.users.public import UserDeleted, UserDeletionRequested


async def sign_out_on_deletion_request(session: AsyncSession, event: UserDeletionRequested) -> None:
    await SessionRepository(session).revoke_all_for_user(event.user_id, SessionRevokeReason.ACCOUNT_DELETED)


async def forget_sign_in_methods(session: AsyncSession, event: UserDeleted) -> None:
    """Personal data: emails, Telegram / Google ids. Removing them also frees them for a new account."""
    await SessionRepository(session).revoke_all_for_user(event.user_id, SessionRevokeReason.ACCOUNT_DELETED)
    await IdentityRepository(session).remove_all_for_user(event.user_id)
