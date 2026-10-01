from typing import Annotated

from fastapi import Depends, Request

from app.core.db import SessionDep
from app.modules.billing.providers.registry import ProviderRegistry
from app.modules.billing.services import CheckoutService, EntitlementService

Session = SessionDep  # scope="function": COMMIT happens before the provider gets its ack


def get_registry(request: Request) -> ProviderRegistry:
    """Built once in create_app() from settings.payment_providers_enabled and stored on app.state."""
    registry: ProviderRegistry = request.app.state.payment_providers
    return registry


Registry = Annotated[ProviderRegistry, Depends(get_registry)]


def get_checkout_service(session: Session, registry: Registry, request: Request) -> CheckoutService:
    return CheckoutService(session, registry, return_url=request.app.state.checkout_return_url)


def get_entitlement_service(session: Session) -> EntitlementService:
    return EntitlementService(session)


Checkout = Annotated[CheckoutService, Depends(get_checkout_service)]
Entitlements = Annotated[EntitlementService, Depends(get_entitlement_service)]
