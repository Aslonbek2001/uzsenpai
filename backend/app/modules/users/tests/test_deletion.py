"""Account deletion: request → sign-out everywhere (durable event) → restore or, after 30 days, anonymize."""

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.outbox import OutboxMessage
from app.modules.users.services import DeletionService


async def outbox_handlers(session: AsyncSession) -> list[str]:
    return list((await session.scalars(select(OutboxMessage.handler).order_by(OutboxMessage.handler))).all())


async def test_request_deletion_then_restore(
    client: AsyncClient, auth_headers: dict[str, str], db_session: AsyncSession
) -> None:
    r = await client.post("/api/v1/users/me/delete", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "deletion_requested" and r.json()["deletion_requested_at"]
    # same transaction as the status change → auth will sign every device out, even if the API crashes now
    assert await outbox_handlers(db_session) == ["auth.sign_out_on_deletion_request"]

    r = await client.post("/api/v1/users/me/restore", headers=auth_headers)
    assert r.json()["status"] == "active" and r.json()["deletion_requested_at"] is None
    r = await client.post("/api/v1/users/me/restore", headers=auth_headers)
    assert r.status_code == 409 and r.json()["error"]["code"] == "users.not_pending_deletion"


async def test_anonymize_only_after_the_grace_period(
    client: AsyncClient, auth_headers: dict[str, str], db_session: AsyncSession, user_id: uuid.UUID
) -> None:
    await client.patch(
        "/api/v1/users/me", json={"residence_country": "JP", "goal": "work", "jlpt_level": "n3"}, headers=auth_headers
    )
    await client.post("/api/v1/users/me/delete", headers=auth_headers)
    service = DeletionService(db_session)

    assert await service.anonymize_due(now=datetime.now(UTC) + timedelta(days=29)) == 0
    assert await service.anonymize_due(now=datetime.now(UTC) + timedelta(days=31)) == 1

    assert "auth.forget_sign_in_methods" in await outbox_handlers(db_session)
    me = await client.get("/api/v1/users/me", headers=auth_headers)
    assert me.status_code == 404  # deleted accounts are gone for the API (this error rolls the test txn back)
