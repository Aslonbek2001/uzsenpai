"""bot/app/main.py — wiring only."""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand
from aiogram.utils.i18n import I18n

from app.config import settings
from app.handlers import language, start  # + menu, resume, interview, visa, orders, learning, fallback
from app.middlewares import BackendUserMiddleware, UzI18nMiddleware
from app.services.api_client import BackendClient

LOCALES = ("uz", "ru", "en", "ja")
i18n = I18n(path="locales", default_locale="uz", domain="messages")


async def set_commands(bot: Bot) -> None:
    # None = default list for Telegram clients in any other language (shown in English)
    for lang in (*LOCALES, None):
        _ = lambda s, lang=lang: i18n.gettext(s, locale=lang or "en")  # noqa: E731
        await bot.set_my_commands(
            [
                BotCommand(command="start", description=_("Main menu")),
                BotCommand(command="resume", description=_("Japanese resume")),
                BotCommand(command="visa", description=_("Visa and documents")),
                BotCommand(command="services", description=_("Paid services")),
                BotCommand(command="orders", description=_("My orders")),
                BotCommand(command="language", description=_("Change language")),
            ],
            language_code=lang,
        )


def build_dispatcher(api: BackendClient) -> Dispatcher:
    dp = Dispatcher(storage=RedisStorage.from_url(settings.redis_url))
    dp["api"] = api  # injected into handlers as `api`
    for observer in (dp.message, dp.callback_query):
        observer.outer_middleware(BackendUserMiddleware(api, i18n))
    UzI18nMiddleware(i18n).setup(dp)
    dp.include_routers(start.router, language.router)  # features…, fallback.router last
    return dp


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    api = BackendClient(settings.backend_url, settings.backend_service_token)
    dp = build_dispatcher(api)
    await set_commands(bot)
    try:
        await dp.start_polling(bot)  # production: webhook via aiohttp + SimpleRequestHandler
    finally:
        await api.close()


if __name__ == "__main__":
    asyncio.run(main())
