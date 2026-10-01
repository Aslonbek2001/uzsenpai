"""Daily: delete refresh-token rows nobody can use any more."""

from app.core.db import unit_of_work
from app.core.tasks import broker
from app.modules.auth.domain.rules import SESSION_PURGE_EXPIRED_AFTER, SESSION_PURGE_REVOKED_AFTER
from app.modules.auth.repositories import SessionRepository


@broker.task(task_name="auth.purge_sessions", schedule=[{"cron": "25 3 * * *"}])
async def purge_sessions() -> None:
    async with unit_of_work() as session:
        await SessionRepository(session).purge(
            expired_for=SESSION_PURGE_EXPIRED_AFTER, revoked_for=SESSION_PURGE_REVOKED_AFTER
        )
