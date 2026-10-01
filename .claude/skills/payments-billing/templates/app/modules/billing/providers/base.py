"""The contract every provider adapter implements. Adapters speak the provider's protocol; business rules
(amount checks, state machine, idempotency, grants) live in services.webhook_service and are reached through
`PaymentLedger`. Adapters must never import repositories or models (enforced by import-linter)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

from fastapi import Request, Response

from app.modules.billing.domain.enums import PaymentStatus, ProviderScope
from app.shared.money import Money


@dataclass(frozen=True)
class ProviderCapabilities:
    scope: ProviderScope
    currencies: frozenset[str]
    refunds: bool = False
    recurring: bool = False
    # False for skeleton/unverified adapters: allowed only when settings.is_local (local/test)
    ready: bool = True


@dataclass(frozen=True)
class CheckoutRequest:
    payment_id: uuid.UUID
    amount: Money
    description: str
    return_url: str
    locale: str


@dataclass(frozen=True)
class CheckoutSession:
    redirect_url: str


@dataclass(frozen=True)
class PaymentView:
    """What an adapter may know about one of our payments."""

    id: uuid.UUID
    amount: Money
    status: PaymentStatus
    provider_txn_id: str | None
    provider_state: dict[str, Any] = field(default_factory=dict)


class PaymentLedger(Protocol):
    """Implemented by services.webhook_service.WebhookLedger; adapters call it while handling a request."""

    async def view(self, payment_id: uuid.UUID) -> PaymentView | None: ...

    async def view_by_provider_txn(self, provider_txn_id: str) -> PaymentView | None: ...

    async def attach_provider_txn(self, payment_id: uuid.UUID, provider_txn_id: str) -> PaymentView: ...

    async def save_provider_state(self, payment_id: uuid.UUID, state: dict[str, Any]) -> PaymentView: ...

    async def mark_paid(self, payment_id: uuid.UUID, *, provider_txn_id: str, amount: Money) -> PaymentView: ...

    async def mark_failed(self, payment_id: uuid.UUID, *, provider_txn_id: str | None) -> PaymentView: ...


class PaymentProvider(Protocol):
    name: str
    capabilities: ProviderCapabilities

    async def create_checkout(self, req: CheckoutRequest) -> CheckoutSession: ...

    async def handle_webhook(self, request: Request, ledger: PaymentLedger) -> Response:
        """Verify signature/auth FIRST, validate the payload, translate it into ledger calls, and return the exact
        response the provider expects. Catch AppError and map it to the provider's own error format."""
        ...
