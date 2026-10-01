import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Index, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Payment(Base):
    __tablename__ = "billing_payments"
    __table_args__ = (
        UniqueConstraint("provider", "provider_txn_id"),
        Index("ix_billing_payments_reuse", "user_id", "product_id", "currency", "provider", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    product_id: Mapped[str] = mapped_column(String(64))  # catalog id — stored, not a cross-module FK
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3))
    provider: Mapped[str] = mapped_column(String(20))
    provider_txn_id: Mapped[str | None] = mapped_column(String(100))
    # Provider protocol data (e.g. Payme txn id/create_time/state) — owned by that provider's adapter
    provider_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # Snapshot at checkout: what this purchase grants, even if the catalog changes before the webhook arrives
    grants_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    fulfilment: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), index=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class PaymentEvent(Base):
    """Append-only audit trail of every status change."""

    __tablename__ = "billing_payment_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    payment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("billing_payments.id"), index=True)
    from_status: Mapped[str] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20))
    provider_txn_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
