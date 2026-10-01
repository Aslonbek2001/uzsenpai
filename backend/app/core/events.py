"""app/core/events.py — event bus: in-process handlers after commit, durable handlers through the outbox.

- `subscribe(Event, fn)`                    → runs in-process after commit; best effort (lost on crash).
- `subscribe_durable(Event, "mod.name", fn)` → `publish(..., durable=True)` writes one outbox row per durable
  handler in the same transaction; the worker runs `fn(session, event)` with retries. The name is stored in the
  database, so never rename a durable handler while rows for it may be pending.
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, TypeVar

from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.ids import uuid7

log = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Durable events must hold JSON-friendly fields only (str, int, bool, UUID, datetime, enums, nested
    dataclasses) — they are stored as JSON and rebuilt in the worker."""

    id: uuid.UUID = field(default_factory=uuid7)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def name(self) -> str:
        return type(self).__name__


E = TypeVar("E", bound=DomainEvent)
Handler = Callable[[Any], Awaitable[None]]
DurableHandler = Callable[[AsyncSession, Any], Awaitable[None]]
OutboxKicker = Callable[[Sequence[uuid.UUID]], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[Handler]] = defaultdict(list)
        self._durable: dict[type[DomainEvent], list[str]] = defaultdict(list)
        self._durable_by_name: dict[str, tuple[type[DomainEvent], DurableHandler]] = {}
        # Set by the composition root: enqueues outbox rows right after commit (the sweeper is the fallback).
        self.on_outbox_committed: OutboxKicker | None = None

    def subscribe(self, event_type: type[E], handler: Callable[[E], Awaitable[None]]) -> None:
        self._handlers[event_type].append(handler)

    def subscribe_durable(
        self, event_type: type[E], name: str, handler: Callable[[AsyncSession, E], Awaitable[None]]
    ) -> None:
        if name in self._durable_by_name:
            raise ValueError(f"durable handler {name!r} is already registered")
        self._durable[event_type].append(name)
        self._durable_by_name[name] = (event_type, handler)

    def durable_handler(self, name: str) -> tuple[type[DomainEvent], DurableHandler] | None:
        return self._durable_by_name.get(name)

    def publish(self, session: AsyncSession, event: DomainEvent, *, durable: bool = False) -> None:
        """Queue an event on the session. durable=True also writes outbox rows in the same transaction."""
        session.info.setdefault("pending_events", []).append(event)
        if not durable:
            return
        from app.core.outbox import OutboxMessage  # local import: outbox → db → events would be a cycle

        payload = TypeAdapter(type(event)).dump_python(event, mode="json")
        for handler_name in self._durable.get(type(event), []):
            row = OutboxMessage(
                id=uuid7(), event_id=event.id, event_name=event.name, handler=handler_name, payload=payload
            )
            session.add(row)
            session.info.setdefault("outbox_ids", []).append(row.id)

    def discard(self, session: AsyncSession) -> None:
        session.info.pop("pending_events", None)
        session.info.pop("outbox_ids", None)

    async def dispatch_committed(self, session: AsyncSession) -> None:
        for event in session.info.pop("pending_events", []):
            for handler in self._handlers.get(type(event), []):
                try:
                    await handler(event)
                except Exception:  # in-process handlers must not break the request
                    log.exception("event handler failed", extra={"event": event.name, "event_id": str(event.id)})
        outbox_ids = session.info.pop("outbox_ids", [])
        if outbox_ids and self.on_outbox_committed is not None:
            try:
                await self.on_outbox_committed(outbox_ids)
            except Exception:  # rows are committed: the sweeper delivers them anyway
                log.warning("outbox kick failed; sweeper will deliver", exc_info=True)


bus = EventBus()
