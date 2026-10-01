from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import Product, ProductPrice


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, product_id: str) -> Product | None:
        return await self.session.get(Product, product_id)

    async def price(self, product_id: str, currency: str) -> ProductPrice | None:
        return await self.session.scalar(
            select(ProductPrice).where(ProductPrice.product_id == product_id, ProductPrice.currency == currency)
        )

    async def active_priced(self, currency: str) -> list[tuple[Product, ProductPrice]]:
        stmt = (
            select(Product, ProductPrice)
            .join(ProductPrice, ProductPrice.product_id == Product.id)
            .where(Product.active.is_(True), ProductPrice.currency == currency)
            .order_by(Product.id)
        )
        return [(p, pr) for p, pr in (await self.session.execute(stmt)).all()]
