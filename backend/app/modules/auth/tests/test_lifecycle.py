"""auth's durable reactions to account deletion, and the session purge."""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.domain.rules import SESSION_PURGE_EXPIRED_AFTER, SESSION_PURGE_REVOKED_AFTER
from app.modules.auth.handlers.user_lifecycle import forget_sign_in_methods, sign_out_on_deletion_request
from app.modules.auth.models import Identity, Session
from app.modules.auth.repositories import SessionRepository
from app.modules.auth.tests.conftest import CapturingSender, bearer, sign_up
from app.modules.users.public import UserDeleted, UserDeletionRequested


async def my_id(client: AsyncClient, tokens: dict[str, str]) -> str:
    return str((await client.get("/api/v1/users/me", headers=bearer(tokens))).json()["id"])


async def test_deletion_request_signs_out_every_device(
    client: AsyncClient, mailbox: CapturingSender, db_session: AsyncSession
) -> None:
    tokens = await sign_up(client, mailbox)
    user_id = await my_id(client, tokens)

    await sign_out_on_deletion_request(db_session, UserDeletionRequested(user_id=user_id))  # type: ignore[arg-type]

    assert (await client.post("/api/v1/auth/refresh")).status_code == 401


async def test_deleted_user_loses_sign_in_methods_and_frees_the_email(
    client: AsyncClient, mailbox: CapturingSender, db_session: AsyncSession
) -> None:
    tokens = await sign_up(client, mailbox)
    user_id = await my_id(client, tokens)

    await forget_sign_in_methods(db_session, UserDeleted(user_id=user_id))  # type: ignore[arg-type]

    assert (await db_session.scalars(select(Identity).where(Identity.subject == "aziz@example.uz"))).all() == []
    await sign_up(client, mailbox)  # the address can be registered again by its owner


async def test_purge_drops_only_long_dead_sessions(
    client: AsyncClient, mailbox: CapturingSender, db_session: AsyncSession
) -> None:
    await sign_up(client, mailbox)
    await client.post("/api/v1/auth/refresh")  # → one rotated (revoked) row + one live row
    await db_session.execute(
        update(Session)
        .where(Session.revoked_at.is_not(None))
        .values(revoked_at=datetime.now(UTC) - SESSION_PURGE_REVOKED_AFTER - timedelta(hours=1))
    )

    purged = await SessionRepository(db_session).purge(
        expired_for=SESSION_PURGE_EXPIRED_AFTER, revoked_for=SESSION_PURGE_REVOKED_AFTER
    )

    assert purged == 1
    assert (await client.post("/api/v1/auth/refresh")).status_code == 200  # the live session survived
