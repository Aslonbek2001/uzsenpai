"""app/core/outbox.py — durable events, written in the same transaction as the change that caused them.

One row per (event, durable handler): a failing handler retries alone, the others are not re-run.
Processing: app/core/outbox_processor.py. Taskiq wiring (kick, sweep, purge): app/core/outbox_tasks.py.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, enum_check, str_enum
from app.shared.ids import uuid7


class OutboxStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"
    DEAD = "dead"  # gave up after MAX_ATTEMPTS — needs a human; never purged automatically


class OutboxMessage(Base):
    __tablename__ = "core_outbox"
    __table_args__ = (
        UniqueConstraint("event_id", "handler"),  # one event reaches one handler once
        enum_check("status", OutboxStatus),
        Index("ix_core_outbox_due", "available_at", postgresql_where=text("status = 'pending'")),
        Index("ix_core_outbox_done", "processed_at", postgresql_where=text("status = 'done'")),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    event_id: Mapped[uuid.UUID]
    event_name: Mapped[str] = mapped_column(String(100))
    handler: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[OutboxStatus] = mapped_column(
        str_enum(OutboxStatus, length=10),
        default=OutboxStatus.PENDING,
        server_default=OutboxStatus.PENDING.value,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
