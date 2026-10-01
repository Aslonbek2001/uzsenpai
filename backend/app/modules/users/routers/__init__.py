"""HTTP layer of the users module: one file per resource, aggregated into one APIRouter."""

from fastapi import APIRouter

from app.modules.users.routers import me

router = APIRouter(prefix="/api/v1/users", tags=["users"])
router.include_router(me.router)

__all__ = ["router"]
