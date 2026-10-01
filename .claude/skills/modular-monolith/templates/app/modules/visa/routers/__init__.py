"""HTTP layer of the visa module: one file per resource, aggregated into one APIRouter."""

from fastapi import APIRouter

from app.modules.visa.routers import status

router = APIRouter(prefix="/api/v1/visa", tags=["visa"])
router.include_router(status.router)
# router.include_router(types.router)          # /visa/types — visa type pages
# router.include_router(consultations.router)  # /visa/consultations — paid, entitlement-gated

__all__ = ["router"]
