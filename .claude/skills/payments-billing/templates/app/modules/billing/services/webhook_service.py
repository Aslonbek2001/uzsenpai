"""The PaymentLedger adapters call: locked, idempotent, amount-checked status changes that grant entitlements."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import bus
from app.modules.billing.domain.enums import PaymentStatus
from app.modules.billing.domain.events import PaymentSucceeded
from app.modules.billing.domain.exceptions import AlreadyPaid, AmountMismatch, PaymentNotFound, TxnAlreadyUsed
from app.modules.billing.domain.state_machine import transition
from app.modules.billing.models import Payment
from app.modules.billing.providers.base import PaymentView
from app.modules.billing.repositories import GrantRepository, PaymentRepository
from app.shared.money import Money


def _view(p: Payment) -> PaymentView:
    return PaymentView(
        p.id, Money(p.amount_minor, p.currency), PaymentStatus(p.status), p.provider_txn_id, dict(p.provider_state)
    )


class WebhookLedger:
    def __init__(self, session: AsyncSession, provider: str) -> None:
        self.session = session
        self.provider = provider
        self.payments = PaymentRepository(session)
        self.grants = GrantRepository(session)

    async def _locked(self, payment_id: uuid.UUID) -> Payment:
        payment = await self.payments.get_for_update(payment_id)
        if payment is None or payment.provider != self.provider:  # never complete via another provider
            raise PaymentNotFound("billing.payment_not_found")
        return payment

    async def view(self, payment_id: uuid.UUID) -> PaymentView | None:
        payment = await self.payments.get(payment_id)
        return _view(payment) if payment and payment.provider == self.provider else None

    async def view_by_provider_txn(self, provider_txn_id: str) -> PaymentView | None:
        payment = await self.payments.get_by_provider_txn(self.provider, provider_txn_id)
        return _view(payment) if payment else None

    async def attach_provider_txn(self, payment_id: uuid.UUID, provider_txn_id: str) -> PaymentView:
        """Link the provider's transaction to our payment before it is paid (Payme CreateTransaction)."""
        payment = await self._locked(payment_id)
        other = await self.payments.get_by_provider_txn(self.provider, provider_txn_id)
        if (other is not None and other.id != payment.id) or (payment.provider_txn_id not in (None, provider_txn_id)):
            raise TxnAlreadyUsed("billing.txn_already_used")
        payment.provider_txn_id = provider_txn_id
        return _view(payment)

    async def save_provider_state(self, payment_id: uuid.UUID, state: dict[str, Any]) -> PaymentView:
        payment = await self._locked(payment_id)
        payment.provider_state = {**payment.provider_state, **state}
        return _view(payment)

    async def mark_paid(self, payment_id: uuid.UUID, *, provider_txn_id: str, amount: Money) -> PaymentView:
        payment = await self._locked(payment_id)
        if payment.status == PaymentStatus.PAID:
            if payment.provider_txn_id == provider_txn_id:
                return _view(payment)  # webhook retry → same answer, nothing granted again
            raise AlreadyPaid("billing.already_paid")  # a different txn must never grant twice
        if amount != Money(payment.amount_minor, payment.currency):
            raise AmountMismatch("billing.amount_mismatch")
        other = await self.payments.get_by_provider_txn(self.provider, provider_txn_id)
        if other is not None and other.id != payment.id:
            raise TxnAlreadyUsed("billing.txn_already_used")

        previous = payment.status
        payment.status = transition(PaymentStatus(previous), PaymentStatus.PAID).value
        payment.provider_txn_id = provider_txn_id
        payment.paid_at = datetime.now(UTC)
        await self.payments.record_event(payment, previous, provider_txn_id)
        self._grant_from_snapshot(payment)
        bus.publish(
            self.session,
            PaymentSucceeded(
                payment_id=payment.id,
                user_id=payment.user_id,
                product_id=payment.product_id,
                fulfilment=payment.fulfilment,
            ),
            durable=True,  # orders + receipt notification must not be lost
        )
        return _view(payment)

    async def mark_failed(self, payment_id: uuid.UUID, *, provider_txn_id: str | None) -> PaymentView:
        payment = await self._locked(payment_id)
        if payment.status in (PaymentStatus.FAILED, PaymentStatus.PAID, PaymentStatus.REFUNDED):
            return _view(payment)  # repeat, or a stale failure after success → keep the stronger state
        previous = payment.status
        payment.status = transition(PaymentStatus(previous), PaymentStatus.FAILED).value
        await self.payments.record_event(payment, previous, provider_txn_id)
        return _view(payment)

    def _grant_from_snapshot(self, payment: Payment) -> None:
        now = datetime.now(UTC)
        for spec in payment.grants_snapshot:
            days = spec.get("days")
            self.grants.add(
                user_id=payment.user_id,
                key=spec["key"],
                source_payment_id=payment.id,
                remaining=spec.get("quantity"),
                expires_at=now + timedelta(days=days) if days else None,
            )
