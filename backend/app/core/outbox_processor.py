"""app/core/outbox_processor.py — delivers outbox rows to their durable handlers.

A row is locked with FOR UPDATE SKIP LOCKED, so the kick task and the sweeper (or two workers) never run the
same row twice at once. The handler runs inside a SAVEPOINT of the same transaction that marks the row done:
its database writes and the "done" mark commit together. External side effects (email, Telegram) are
at-least-once — handlers dedupe by `event.id`.
"""

import logging
import uuid
from datetime import timedelta

from pydantic import TypeAdapter
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db import SessionFactory
from app.core.events import EventBus, bus
from app.core.outbox import OutboxMessage, OutboxStatus

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 10
RETENTION = timedelta(days=30)
SWEEP_BATCH = 100


def backoff(attempts: int) -> timedelta:
    """5s, 10s, 20s … capped at 1 hour (10 attempts ≈ 85 minutes in total)."""
    return timedelta(seconds=min(5 * 2 ** (attempts - 1), 3600))


async def process_message(
    message_id: uuid.UUID,
    *,
    session_factory: async_sessionmaker[AsyncSession] = SessionFactory,
    event_bus: EventBus = bus,
) -> bool:
    """Run one due row. True = handled now; False = not due, already taken, or failed (retry scheduled)."""
    async with session_factory() as session:
        msg = await session.scalar(
            select(OutboxMessage)
            .where(
                OutboxMessage.id == message_id,
                OutboxMessage.status == OutboxStatus.PENDING,
                OutboxMessage.available_at <= func.now(),
            )
            .with_for_update(skip_locked=True)
        )
        if msg is None:
            return False
        try:
            entry = event_bus.durable_handler(msg.handler)
            if entry is None:
                raise LookupError(f"no durable handler registered as {msg.handler!r}")
            event_type, handler = entry
            event = TypeAdapter(event_type).validate_python(msg.payload)
            async with session.begin_nested():  # handler failure rolls back only its own writes
                await handler(session, event)
        except Exception as exc:
            event_bus.discard(session)
            _record_failure(msg, exc)
            await session.commit()
            return False
        msg.status = OutboxStatus.DONE
        msg.processed_at = func.now()
        await session.commit()
        await event_bus.dispatch_committed(session)  # events the handler itself published
        return True


def _record_failure(msg: OutboxMessage, exc: Exception) -> None:
    msg.attempts += 1
    msg.last_error = f"{type(exc).__name__}: {exc}"[:2000]
    context = {"outbox_id": str(msg.id), "handler": msg.handler, "event": msg.event_name, "attempts": msg.attempts}
    if msg.attempts >= MAX_ATTEMPTS:
        msg.status = OutboxStatus.DEAD
        log.error("outbox message is dead — needs manual replay", extra=context, exc_info=exc)
    else:
        msg.available_at = func.now() + backoff(msg.attempts)
        log.warning("outbox handler failed — will retry", extra=context, exc_info=exc)


async def sweep(
    *, session_factory: async_sessionmaker[AsyncSession] = SessionFactory, event_bus: EventBus = bus
) -> int:
    """Deliver due rows whose kick was lost (Redis down, worker crash) or whose retry time has come."""
    async with session_factory() as session:
        ids = (
            await session.scalars(
                select(OutboxMessage.id)
                .where(OutboxMessage.status == OutboxStatus.PENDING, OutboxMessage.available_at <= func.now())
                .order_by(OutboxMessage.available_at)
                .limit(SWEEP_BATCH)
            )
        ).all()
    handled = 0
    for message_id in ids:
        handled += await process_message(message_id, session_factory=session_factory, event_bus=event_bus)
    return handled


async def purge_processed(*, session_factory: async_sessionmaker[AsyncSession] = SessionFactory) -> int:
    """Delete rows delivered more than RETENTION ago. Dead rows are kept until a human deals with them."""
    async with session_factory() as session:
        result = await session.execute(
            delete(OutboxMessage).where(
                OutboxMessage.status == OutboxStatus.DONE,
                OutboxMessage.processed_at < func.now() - RETENTION,
            )
        )
        await session.commit()
    return int(result.rowcount)  # type: ignore[attr-defined]
