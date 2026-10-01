"""Start a payment: server-side price from catalog → pending Payment → provider checkout session."""

import uuid
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.domain.enums import PaymentStatus
from app.modules.billing.models import Payment
from app.modules.billing.providers.base import CheckoutRequest
from app.modules.billing.providers.registry import ProviderRegistry
from app.modules.billing.repositories import PaymentRepository
from app.modules.billing.schemas import CheckoutIn, CheckoutOut
from app.modules.catalog.public import CatalogFacade

REUSE_PENDING_FOR = timedelta(minutes=30)


class CheckoutService:
    def __init__(self, session: AsyncSession, registry: ProviderRegistry, return_url: str) -> None:
        self.payments = PaymentRepository(session)
        self.catalog = CatalogFacade(session)
        self.registry = registry
        self.return_url = return_url

    async def start(self, user_id: uuid.UUID, data: CheckoutIn, locale: str) -> CheckoutOut:
        product = await self.catalog.priced(data.product_id, data.currency)  # the client never sends an amount
        provider = self.registry.choose(data.currency, data.provider)
        payment = await self.payments.recent_pending(
            user_id=user_id,
            product_id=product.id,
            currency=product.price.currency,
            provider=provider.name,
            since=datetime.now(UTC) - REUSE_PENDING_FOR,
        )
        if payment is None or payment.amount_minor != product.price.amount_minor:
            payment = await self.payments.add(
                Payment(
                    user_id=user_id,
                    product_id=product.id,
                    amount_minor=product.price.amount_minor,
                    currency=product.price.currency,
                    provider=provider.name,
                    provider_state={},
                    grants_snapshot=[asdict(g) for g in product.grants],
                    fulfilment=product.fulfilment,
                    status=PaymentStatus.PENDING.value,
                )
            )
        session = await provider.create_checkout(
            CheckoutRequest(payment.id, product.price, product.id, self.return_url, locale)
        )
        return CheckoutOut(payment_id=payment.id, provider=provider.name, redirect_url=session.redirect_url)
