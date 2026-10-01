"""Test factories other modules' tests may use (the only cross-module import allowed besides `public`)."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import Product, ProductPrice


async def create_product(
    session: AsyncSession,
    product_id: str,
    *,
    prices: dict[str, int],
    grants: list[dict[str, Any]],
    fulfilment: str = "ai",
    title_uz: str = "Mahsulot",
) -> str:
    session.add(Product(id=product_id, title={"uz": title_uz}, includes=[], grants=grants, fulfilment=fulfilment))
    session.add_all([ProductPrice(product_id=product_id, currency=c, amount_minor=a) for c, a in prices.items()])
    await session.flush()
    return product_id


async def set_product_active(session: AsyncSession, product_id: str, *, active: bool) -> None:
    product = await session.get(Product, product_id)
    if product is None:
        raise LookupError(product_id)
    product.active = active
    await session.flush()
