"""bot/app/handlers/language.py — language picker with CallbackData (start flow lives in start.py)."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.i18n import I18n
from aiogram.utils.i18n import gettext as _
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.middlewares import forget_user
from app.services.api_client import BackendClient, BotUser

router = Router(name="language")

# Shown in their own language — never flags
LANGUAGE_NAMES = {"uz": "Oʻzbekcha", "ru": "Русский", "en": "English", "ja": "日本語"}


class LangCb(CallbackData, prefix="lang"):
    code: str


def language_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for code, name in LANGUAGE_NAMES.items():
        kb.button(text=name, callback_data=LangCb(code=code))
    kb.adjust(2)
    return kb.as_markup()


@router.message(Command("language"))
async def ask_language(message: Message) -> None:
    await message.answer(_("Choose your language"), reply_markup=language_keyboard())


@router.callback_query(LangCb.filter(F.code.in_(LANGUAGE_NAMES)))
async def set_language(query: CallbackQuery, callback_data: LangCb, api: BackendClient, user: BotUser, i18n: I18n) -> None:
    await api.update_locale(query.from_user.id, callback_data.code)
    forget_user(query.from_user.id)  # next update re-reads the profile with the new locale
    i18n.ctx_locale.set(callback_data.code)  # reply in the new language right away
    await query.answer()
    if query.message is not None:
        await query.message.answer(_("Language changed."))


# --- bot/app/handlers/start.py ---
# router = Router(name="start")
#
# @router.message(CommandStart())
# async def start(message: Message, user: BotUser) -> None:
#     if not user.language_confirmed:
#         await message.answer(_("Choose your language"), reply_markup=language_keyboard())
#         return
#     await message.answer(_("Welcome to UzSenpai! What would you like to do?"), reply_markup=main_menu())
