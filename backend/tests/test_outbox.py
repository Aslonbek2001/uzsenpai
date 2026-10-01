"""Outbox delivery with REAL commits (the processor opens its own sessions, like the worker does)."""

import asyncio
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.events import DomainEvent, EventBus
from app.core.outbox import OutboxMessage, OutboxStatus
from app.core.outbox_processor import MAX_ATTEMPTS, process_message, purge_processed, sweep


@dataclass(frozen=True, kw_only=True)
class OrderPaid(DomainEvent):
    order_id: uuid.UUID
    amount_minor: int


@pytest.fixture
async def factory(engine: AsyncEngine) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    yield async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.execute(delete(OutboxMessage))


class Recorder:
    """Durable handler that records events and can be told to fail."""

    def __init__(self, fail: bool = False) -> None:
        self.events: list[OrderPaid] = []
        self.fail = fail

    async def __call__(self, session: AsyncSession, event: OrderPaid) -> None:
        self.events.append(event)
        if self.fail:
            # a write that must be rolled back together with the failure
            session.add(OutboxMessage(event_id=uuid.uuid4(), event_name="Junk", handler="junk", payload={}))
            await session.flush()
            raise RuntimeError("boom")


async def publish(factory: async_sessionmaker[AsyncSession], bus: EventBus, event: DomainEvent) -> list[OutboxMessage]:
    async with factory() as session:
        bus.publish(session, event, durable=True)
        await session.commit()
        return list((await session.scalars(select(OutboxMessage).where(OutboxMessage.event_id == event.id))).all())


def paid_event() -> OrderPaid:
    return OrderPaid(order_id=uuid.uuid4(), amount_minor=15_000_000)


async def test_durable_publish_writes_one_row_per_handler(factory: async_sessionmaker[AsyncSession]) -> None:
    bus = EventBus()
    bus.subscribe_durable(OrderPaid, "orders.on_paid", Recorder())
    bus.subscribe_durable(OrderPaid, "notifications.on_paid", Recorder())
    event = paid_event()
    rows = await publish(factory, bus, event)
    assert sorted(r.handler for r in rows) == ["notifications.on_paid", "orders.on_paid"]
    assert all(r.status == OutboxStatus.PENDING and r.event_name == "OrderPaid" for r in rows)
    assert rows[0].payload["order_id"] == str(event.order_id)


async def test_success_marks_done_and_rebuilds_the_event(factory: async_sessionmaker[AsyncSession]) -> None:
    bus, handler = EventBus(), Recorder()
    bus.subscribe_durable(OrderPaid, "orders.on_paid", handler)
    event = paid_event()
    [row] = await publish(factory, bus, event)

    assert await process_message(row.id, session_factory=factory, event_bus=bus) is True

    assert handler.events == [event]
    async with factory() as session:
        stored = await session.get_one(OutboxMessage, row.id)
        assert stored.status == OutboxStatus.DONE
        assert stored.processed_at is not None
    # already done → never runs twice
    assert await process_message(row.id, session_factory=factory, event_bus=bus) is False
    assert len(handler.events) == 1


async def test_failure_schedules_retry_and_rolls_back_handler_writes(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    bus = EventBus()
    bus.subscribe_durable(OrderPaid, "orders.on_paid", Recorder(fail=True))
    [row] = await publish(factory, bus, paid_event())

    assert await process_message(row.id, session_factory=factory, event_bus=bus) is False

    async with factory() as session:
        stored = await session.get_one(OutboxMessage, row.id)
        assert stored.status == OutboxStatus.PENDING
        assert stored.attempts == 1
        assert stored.last_error == "RuntimeError: boom"
        assert stored.available_at > datetime.now(UTC)  # backed off: not due yet
        assert await session.scalar(select(OutboxMessage).where(OutboxMessage.handler == "junk")) is None


async def test_gives_up_after_max_attempts(factory: async_sessionmaker[AsyncSession]) -> None:
    bus = EventBus()
    bus.subscribe_durable(OrderPaid, "orders.on_paid", Recorder(fail=True))
    [row] = await publish(factory, bus, paid_event())
    async with factory() as session:
        await session.execute(update(OutboxMessage).where(OutboxMessage.id == row.id).values(attempts=MAX_ATTEMPTS - 1))
        await session.commit()

    await process_message(row.id, session_factory=factory, event_bus=bus)

    async with factory() as session:
        stored = await session.get_one(OutboxMessage, row.id)
        assert stored.status == OutboxStatus.DEAD
        assert stored.attempts == MAX_ATTEMPTS


async def test_unknown_handler_counts_as_failure(factory: async_sessionmaker[AsyncSession]) -> None:
    publisher = EventBus()
    publisher.subscribe_durable(OrderPaid, "orders.removed_handler", Recorder())
    [row] = await publish(factory, publisher, paid_event())

    assert await process_message(row.id, session_factory=factory, event_bus=EventBus()) is False

    async with factory() as session:
        stored = await session.get_one(OutboxMessage, row.id)
        assert stored.attempts == 1
        assert stored.last_error is not None and "orders.removed_handler" in stored.last_error


async def test_sweep_delivers_only_due_rows(factory: async_sessionmaker[AsyncSession]) -> None:
    bus, handler = EventBus(), Recorder()
    bus.subscribe_durable(OrderPaid, "orders.on_paid", handler)
    [due] = await publish(factory, bus, paid_event())
    [later] = await publish(factory, bus, paid_event())
    async with factory() as session:
        await session.execute(
            update(OutboxMessage)
            .where(OutboxMessage.id == later.id)
            .values(available_at=datetime.now(UTC) + timedelta(minutes=5))
        )
        await session.commit()

    assert await sweep(session_factory=factory, event_bus=bus) == 1
    assert [e.id for e in handler.events] == [due.event_id]


async def test_concurrent_delivery_runs_the_handler_once(factory: async_sessionmaker[AsyncSession]) -> None:
    calls = 0

    async def slow_handler(session: AsyncSession, event: OrderPaid) -> None:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.2)  # hold the row lock while the second delivery tries

    bus = EventBus()
    bus.subscribe_durable(OrderPaid, "orders.on_paid", slow_handler)
    [row] = await publish(factory, bus, paid_event())

    results = await asyncio.gather(
        process_message(row.id, session_factory=factory, event_bus=bus),
        process_message(row.id, session_factory=factory, event_bus=bus),
    )

    assert sorted(results) == [False, True]
    assert calls == 1


async def test_purge_keeps_recent_and_dead_rows(factory: async_sessionmaker[AsyncSession]) -> None:
    bus = EventBus()
    bus.subscribe_durable(OrderPaid, "orders.on_paid", Recorder())
    old, recent, dead = [(await publish(factory, bus, paid_event()))[0] for _ in range(3)]
    long_ago = datetime.now(UTC) - timedelta(days=31)
    async with factory() as session:
        for row_id, status, processed_at in [
            (old.id, OutboxStatus.DONE, long_ago),
            (recent.id, OutboxStatus.DONE, datetime.now(UTC)),
            (dead.id, OutboxStatus.DEAD, long_ago),
        ]:
            await session.execute(
                update(OutboxMessage).where(OutboxMessage.id == row_id).values(status=status, processed_at=processed_at)
            )
        await session.commit()

    assert await purge_processed(session_factory=factory) == 1

    async with factory() as session:
        remaining = set((await session.scalars(select(OutboxMessage.id))).all())
    assert remaining == {recent.id, dead.id}


def test_durable_handler_names_are_unique() -> None:
    bus = EventBus()
    bus.subscribe_durable(OrderPaid, "orders.on_paid", Recorder())
    with pytest.raises(ValueError, match="already registered"):
        bus.subscribe_durable(OrderPaid, "orders.on_paid", Recorder())
