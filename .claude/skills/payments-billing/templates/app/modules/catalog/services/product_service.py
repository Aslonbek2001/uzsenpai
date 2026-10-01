"""Localized product cards for the website and the bot."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.domain.exceptions import PriceNotAvailable, ProductNotFound
from app.modules.catalog.models import Product
from app.modules.catalog.repositories import ProductRepository
from app.modules.catalog.schemas import PriceOut, ProductOut
from app.shared.i18n import Locale, LocalizedText


def _card(product: Product, amount_minor: int, currency: str, locale: Locale) -> ProductOut:
    title, lang = LocalizedText.model_validate(product.title).resolve(locale)
    includes = [LocalizedText.model_validate(i).resolve(locale)[0] for i in product.includes]
    return ProductOut(
        id=product.id,
        title=title,
        includes=includes,
        lang=lang.value,
        fulfilment=product.fulfilment,
        price=PriceOut(amount_minor=amount_minor, currency=currency),
    )


class ProductService:
    def __init__(self, session: AsyncSession) -> None:
        self.products = ProductRepository(session)

    async def list(self, currency: str, locale: Locale) -> list[ProductOut]:
        return [
            _card(p, price.amount_minor, currency, locale) for p, price in await self.products.active_priced(currency)
        ]

    async def get(self, product_id: str, currency: str, locale: Locale) -> ProductOut:
        product = await self.products.get(product_id)
        if product is None or not product.active:
            raise ProductNotFound("catalog.product_not_found", params={"product_id": product_id})
        price = await self.products.price(product_id, currency)
        if price is None:
            raise PriceNotAvailable("catalog.price_not_available", params={"currency": currency})
        return _card(product, price.amount_minor, currency, locale)
