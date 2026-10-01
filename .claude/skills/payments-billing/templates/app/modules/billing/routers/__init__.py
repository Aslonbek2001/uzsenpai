from fastapi import APIRouter

from app.modules.billing.routers import checkout, entitlements, webhooks

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])
router.include_router(checkout.router)
router.include_router(entitlements.router)
router.include_router(webhooks.router)

__all__ = ["router"]
