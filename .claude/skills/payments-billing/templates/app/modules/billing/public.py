"""billing's only importable surface: access checks for paid features + the provider registry builder."""

import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.db import SessionDep
from app.modules.auth.public import CurrentUser, current_user
from app.modules.billing.domain.events import PaymentSucceeded
from app.modules.billing.domain.exceptions import NoEntitlement
from app.modules.billing.providers.base import PaymentProvider
from app.modules.billing.providers.click import ClickProvider
from app.modules.billing.providers.fake import FakeProvider
from app.modules.billing.providers.payme import PaymeProvider
from app.modules.billing.providers.registry import ProviderRegistry
from app.modules.billing.services import EntitlementService

DEV_FAKE_SECRET = "local-dev-only"  # noqa: S105 — dev default; refused outside local/test


class BillingFacade:
    def __init__(self, session: AsyncSession) -> None:
        self._entitlements = EntitlementService(session)

    async def has_access(self, user_id: uuid.UUID, key: str) -> bool:
        return await self._entitlements.has_access(user_id, key)

    async def consume(self, user_id: uuid.UUID, key: str) -> None:
        """Call after the paid action succeeded (e.g. the mock-interview report was generated)."""
        await self._entitlements.consume(user_id, key)


def require_entitlement(key: str) -> Callable[..., Awaitable[None]]:
    """Router dependency in any module: dependencies=[Depends(require_entitlement(Key.RESUME_PDF_EXPORT))]."""

    async def _check(user: Annotated[CurrentUser, Depends(current_user)], session: SessionDep) -> None:
        if not await EntitlementService(session).has_access(user.id, key):
            raise NoEntitlement("billing.no_entitlement", params={"key": key})

    return _check


def _require(settings: Settings, provider: str, *fields: str) -> None:
    missing = [f for f in fields if not getattr(settings, f)]
    if missing:
        raise RuntimeError(f"payment provider {provider!r} enabled but not configured: {', '.join(missing)}")


def build_provider_registry(settings: Settings) -> ProviderRegistry:
    """Called once by create_app(). Fails fast on misconfiguration instead of accepting unsafe webhooks.

    - only providers in PAYMENT_PROVIDERS_ENABLED are active, each must have its credentials;
    - `fake` and adapters with capabilities.ready=False (skeletons) are allowed only when settings.is_local.
    """

    def payme() -> PaymentProvider:
        _require(settings, "payme", "payme_merchant_id", "payme_key")
        return PaymeProvider(settings.payme_merchant_id, settings.payme_key, settings.payme_checkout_url)

    def click() -> PaymentProvider:
        _require(settings, "click", "click_service_id", "click_merchant_id", "click_secret_key")
        return ClickProvider(
            settings.click_service_id,
            settings.click_merchant_id,
            settings.click_secret_key,
            settings.click_checkout_url,
        )

    def fake() -> PaymentProvider:
        if not settings.is_local:
            raise RuntimeError("the fake payment provider is allowed only in local/test environments")
        return FakeProvider(settings.fake_provider_secret)

    factories: dict[str, Callable[[], PaymentProvider]] = {"payme": payme, "click": click, "fake": fake}
    # "uzum": …, international provider: … — added by ADR, same PaymentProvider contract
    unknown = set(settings.payment_providers_enabled) - factories.keys()
    if unknown:
        raise RuntimeError(f"unknown payment providers enabled: {sorted(unknown)}")
    providers = [factories[name]() for name in settings.payment_providers_enabled]
    not_ready = [p.name for p in providers if not p.capabilities.ready]
    if not_ready and not settings.is_local:
        raise RuntimeError(f"payment adapters not production-ready (verify against docs first): {not_ready}")
    return ProviderRegistry(providers)


__all__ = ["DEV_FAKE_SECRET", "BillingFacade", "PaymentSucceeded", "build_provider_registry", "require_entitlement"]
