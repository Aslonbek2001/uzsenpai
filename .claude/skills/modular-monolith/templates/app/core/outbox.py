"""app/core/outbox.py — durable events written in the same transaction as the change that caused them.

The Taskiq worker polls rows with processed_at IS NULL, runs the registered durable handler (idempotent by id),
then sets processed_at. Failed handlers are retried with backoff; after N attempts the row is flagged.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class OutboxMessage(Base):
    __tablename__ = "core_outbox"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
