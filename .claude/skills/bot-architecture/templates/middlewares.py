"""bot/app/middlewares/__init__.py — backend user resolution (cached) and per-user locale."""
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User
from aiogram.utils.i18n import I18n, I18nMiddleware

from app.services.api_client import BackendClient, BackendError, BotUser

log = logging.getLogger(__name__)
SUPPORTED = {"uz", "ru", "en", "ja"}
_CACHE_TTL = 60.0
_cache: dict[int, tuple[float, BotUser]] = {}


def guess_locale(tg_user: User | None) -> str:
    code = (tg_user.language_code or "")[:2] if tg_user else ""
    return code if code in SUPPORTED else "uz"


def forget_user(telegram_id: int) -> None:
    """Call after changing the profile (e.g. language) so the next update re-reads it."""
    _cache.pop(telegram_id, None)


class BackendUserMiddleware(BaseMiddleware):
    """Puts `user` (backend profile) and `locale` into handler data. One backend call per user per minute."""

    def __init__(self, api: BackendClient, i18n: I18n) -> None:
        self.api = api
        self.i18n = i18n

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: User | None = data.get("event_from_user")
        if tg_user is None:
            return await handler(event, data)

        cached = _cache.get(tg_user.id)
        if cached and time.monotonic() - cached[0] < _CACHE_TTL:
            user = cached[1]
        else:
            try:
                user = await self.api.get_or_create_telegram_user(
                    telegram_id=tg_user.id, first_name=tg_user.first_name, locale_hint=guess_locale(tg_user)
                )
            except BackendError:
                log.exception("backend unavailable for telegram user %s", tg_user.id)
                text = self.i18n.gettext("Service is temporarily unavailable. Please try again in a minute.",
                                         locale=guess_locale(tg_user))
                if isinstance(event, Message):
                    await event.answer(text)
                elif isinstance(event, CallbackQuery):
                    await event.answer(text, show_alert=True)
                return None
            _cache[tg_user.id] = (time.monotonic(), user)

        data["user"] = user
        data["locale"] = user.locale
        return await handler(event, data)


class UzI18nMiddleware(I18nMiddleware):
    """Locale comes from the backend profile (shared with the website)."""

    async def get_locale(self, event: TelegramObject, data: dict[str, Any]) -> str:
        locale = data.get("locale")
        return locale if locale in SUPPORTED else "uz"
