"""catalog's only importable surface. Prices live here and nowhere else."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.domain.exceptions import PriceNotAvailable, ProductNotFound
from app.modules.catalog.domain.keys import Key
from app.modules.catalog.repositories import ProductRepository
from app.shared.money import Money


@dataclass(frozen=True)
class GrantSpec:
    key: str
    quantity: int | None  # None = unlimited
    days: int | None  # None = never expires


@dataclass(frozen=True)
class PricedProduct:
    id: str
    price: Money
    grants: tuple[GrantSpec, ...]
    fulfilment: str


class CatalogFacade:
    def __init__(self, session: AsyncSession) -> None:
        self._products = ProductRepository(session)

    async def priced(self, product_id: str, currency: str) -> PricedProduct:
        product = await self._products.get(product_id)
        if product is None or not product.active:
            raise ProductNotFound("catalog.product_not_found", params={"product_id": product_id})
        price = await self._products.price(product_id, currency)
        if price is None:
            raise PriceNotAvailable("catalog.price_not_available", params={"currency": currency})
        try:
            money = Money(price.amount_minor, price.currency)
        except (TypeError, ValueError):  # bad catalog row (e.g. unsupported currency) → not sellable, not a 500
            raise PriceNotAvailable("catalog.price_not_available", params={"currency": currency}) from None
        grants = tuple(GrantSpec(g["key"], g.get("quantity"), g.get("days")) for g in product.grants)
        return PricedProduct(product.id, money, grants, product.fulfilment)


__all__ = ["CatalogFacade", "GrantSpec", "Key", "PricedProduct"]
