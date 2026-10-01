"""/api/v1/auth/bot/* — called only by the Telegram bot with its service token."""

from fastapi import APIRouter, Depends

from app.modules.auth.routers.deps import TelegramAuth, require_bot
from app.modules.auth.schemas import BotUserIn, BotUserOut

router = APIRouter(prefix="/bot", dependencies=[Depends(require_bot)])


@router.post("/users", response_model=BotUserOut)
async def resolve_user(data: BotUserIn, auth: TelegramAuth) -> BotUserOut:
    """Find or create the user behind a Telegram id (every new chat / bot restart)."""
    user, created = await auth.resolve_or_create(data.telegram_id, data.first_name, data.locale_hint)
    return BotUserOut(user_id=user.id, display_name=user.display_name, locale=user.locale, created=created)
