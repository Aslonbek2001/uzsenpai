"""app/core/events.py — in-process event bus with after-commit dispatch and a durable outbox."""

from __future__ import annotations

import json
import logging
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def name(self) -> str:
        return type(self).__name__


E = TypeVar("E", bound=DomainEvent)
Handler = Callable[[Any], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type[E], handler: Callable[[E], Awaitable[None]]) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, session: AsyncSession, event: DomainEvent, *, durable: bool = False) -> None:
        """Queue an event on the session. durable=True also writes it to the outbox in the same transaction."""
        session.info.setdefault("pending_events", []).append(event)
        if durable:
            from app.core.outbox import OutboxMessage  # local import avoids a cycle with db.Base

            session.add(
                OutboxMessage(id=event.id, name=event.name, payload=json.loads(json.dumps(asdict(event), default=str)))
            )

    def discard(self, session: AsyncSession) -> None:
        session.info.pop("pending_events", None)

    async def dispatch_committed(self, session: AsyncSession) -> None:
        for event in session.info.pop("pending_events", []):
            for handler in self._handlers.get(type(event), []):
                try:
                    await handler(event)
                except Exception:  # in-process handlers must not break the request
                    log.exception("event handler failed", extra={"event": event.name, "event_id": event.id})


bus = EventBus()
