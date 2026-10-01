"""/api/v1/auth/telegram/* — website sign-in with the Telegram Login Widget."""

from fastapi import APIRouter, Response

from app.modules.auth.routers.cookies import tokens_response
from app.modules.auth.routers.deps import Client, RequestLocale, TelegramAuth
from app.modules.auth.schemas import TelegramLoginIn, TokenOut

router = APIRouter(prefix="/telegram")


@router.post("/login", response_model=TokenOut)
async def login(
    data: TelegramLoginIn, auth: TelegramAuth, locale: RequestLocale, client: Client, response: Response
) -> TokenOut:
    return tokens_response(response, await auth.login_widget(data, locale, client))
