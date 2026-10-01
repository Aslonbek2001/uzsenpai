"""Which providers are enabled and which ones may serve a currency."""

from app.modules.billing.domain.enums import ProviderScope
from app.modules.billing.domain.exceptions import ProviderNotAvailable
from app.modules.billing.providers.base import PaymentProvider


class ProviderRegistry:
    def __init__(self, providers: list[PaymentProvider]) -> None:
        self._by_name = {p.name: p for p in providers}

    def get(self, name: str) -> PaymentProvider:
        provider = self._by_name.get(name)
        if provider is None:
            raise ProviderNotAvailable("billing.provider_not_available", params={"provider": name})
        return provider

    def for_currency(self, currency: str) -> list[PaymentProvider]:
        """Providers that accept the currency — national first for UZS, international first otherwise."""
        preferred = ProviderScope.NATIONAL if currency == "UZS" else ProviderScope.INTERNATIONAL
        options = [p for p in self._by_name.values() if currency in p.capabilities.currencies]
        return sorted(options, key=lambda p: p.capabilities.scope != preferred)

    def choose(self, currency: str, preferred: str | None) -> PaymentProvider:
        options = self.for_currency(currency)
        if not options:
            raise ProviderNotAvailable("billing.no_provider_for_currency", params={"currency": currency})
        if preferred is None:
            return options[0]
        for p in options:
            if p.name == preferred:
                return p
        raise ProviderNotAvailable("billing.provider_not_available", params={"provider": preferred})
