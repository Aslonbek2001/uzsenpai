import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.models import Payment, PaymentEvent


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, payment: Payment) -> Payment:
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def get(self, payment_id: uuid.UUID) -> Payment | None:
        return await self.session.get(Payment, payment_id)

    async def get_for_update(self, payment_id: uuid.UUID) -> Payment | None:
        """Row lock: concurrent webhook retries for the same payment are serialized."""
        return await self.session.scalar(select(Payment).where(Payment.id == payment_id).with_for_update())

    async def get_by_provider_txn(self, provider: str, provider_txn_id: str) -> Payment | None:
        return await self.session.scalar(
            select(Payment).where(Payment.provider == provider, Payment.provider_txn_id == provider_txn_id)
        )

    async def recent_pending(
        self, *, user_id: uuid.UUID, product_id: str, currency: str, provider: str, since: datetime
    ) -> Payment | None:
        """Reuse an open checkout instead of piling up pending rows on every click."""
        return await self.session.scalar(
            select(Payment)
            .where(
                Payment.user_id == user_id,
                Payment.product_id == product_id,
                Payment.currency == currency,
                Payment.provider == provider,
                Payment.status == "pending",
                Payment.created_at >= since,
            )
            .order_by(Payment.created_at.desc())
            .limit(1)
        )

    async def record_event(self, payment: Payment, from_status: str, provider_txn_id: str | None) -> None:
        self.session.add(
            PaymentEvent(
                payment_id=payment.id,
                from_status=from_status,
                to_status=payment.status,
                provider_txn_id=provider_txn_id,
            )
        )
