"""Public catalog: GET /api/v1/catalog/products?currency=UZS and /products/{id}?currency=JPY (no auth)."""

from typing import Annotated

from fastapi import APIRouter, Query, Request

from app.modules.catalog.routers.deps import Products
from app.modules.catalog.schemas import ProductOut
from app.shared.i18n import locale_from_request

router = APIRouter(prefix="/products")
Currency = Annotated[str, Query(pattern="^[A-Z]{3}$", description="UZS (national) or USD/JPY/EUR (international)")]


@router.get("", response_model=list[ProductOut])
async def list_products(request: Request, service: Products, currency: Currency = "UZS") -> list[ProductOut]:
    return await service.list(currency, locale_from_request(request))


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: str, request: Request, service: Products, currency: Currency = "UZS") -> ProductOut:
    return await service.get(product_id, currency, locale_from_request(request))
