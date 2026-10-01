"""HTTP layer of the auth module: one file per resource, aggregated into one APIRouter."""

from fastapi import APIRouter

from app.modules.auth.routers import bot, email, sessions, telegram

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
router.include_router(email.router)
router.include_router(telegram.router)
router.include_router(sessions.router)
router.include_router(bot.router)

__all__ = ["router"]
