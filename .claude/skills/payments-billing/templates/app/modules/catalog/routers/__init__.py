from fastapi import APIRouter

from app.modules.catalog.routers import products

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])
router.include_router(products.router)

__all__ = ["router"]
