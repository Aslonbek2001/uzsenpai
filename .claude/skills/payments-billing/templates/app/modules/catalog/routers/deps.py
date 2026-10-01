from typing import Annotated

from fastapi import Depends

from app.core.db import SessionDep
from app.modules.catalog.services import ProductService


def get_product_service(session: SessionDep) -> ProductService:
    return ProductService(session)


Products = Annotated[ProductService, Depends(get_product_service)]
