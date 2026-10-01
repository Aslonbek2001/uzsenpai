"""Telegram: website sign-in (Login Widget) and the bot resolving / creating the user behind a Telegram id."""

import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.auth.domain.enums import AuthProvider
from app.modules.auth.domain.exceptions import InvalidTelegramData
from app.modules.auth.domain.rules import TELEGRAM_AUTH_MAX_AGE
from app.modules.auth.providers.telegram import verify_login_widget
from app.modules.auth.repositories import IdentityRepository
from app.modules.auth.schemas import TelegramLoginIn
from app.modules.auth.services.session_service import ClientInfo, IssuedTokens, SessionService
from app.modules.users.public import UserDTO, UsersFacade
from app.shared.i18n import Locale


class TelegramAuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.identities = IdentityRepository(session)
        self.users = UsersFacade(session)
        self.sessions = SessionService(session)

    @staticmethod
    def verify(data: TelegramLoginIn) -> None:
        valid = verify_login_widget(
            data.signed_fields(),
            bot_token=settings.telegram_bot_token,
            now=int(time.time()),
            max_age=TELEGRAM_AUTH_MAX_AGE,
        )
        if not valid:
            raise InvalidTelegramData("auth.invalid_telegram_data")

    async def login_widget(self, data: TelegramLoginIn, locale: Locale, client: ClientInfo) -> IssuedTokens:
        self.verify(data)
        name = " ".join(part for part in (data.first_name, data.last_name) if part)
        user, _ = await self.resolve_or_create(data.id, name, locale)
        return await self.sessions.start(user, client)

    async def resolve_or_create(self, telegram_id: int, display_name: str, locale: Locale) -> tuple[UserDTO, bool]:
        """(user, created). Called by the bot on every new chat and by the widget sign-in."""
        identity = await self.identities.get(AuthProvider.TELEGRAM, str(telegram_id))
        if identity is not None:
            user = await self.users.get(identity.user_id)
            if user is not None:
                await self.identities.touch_login(identity)
                return user, False
        user = await self.users.create(display_name=display_name, locale=locale)
        await self.identities.add(user_id=user.id, provider=AuthProvider.TELEGRAM, subject=str(telegram_id))
        return user, True
