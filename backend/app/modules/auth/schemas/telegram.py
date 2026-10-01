"""API contract for Telegram sign-in (website widget) and the bot's user resolution."""

import uuid

from pydantic import BaseModel, Field

from app.shared.i18n import Locale


class TelegramLoginIn(BaseModel):
    """Fields exactly as the Telegram Login Widget returns them (all are part of the signature)."""

    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str

    def signed_fields(self) -> dict[str, str]:
        return {k: str(v) for k, v in self.model_dump(exclude_none=True).items()}


class BotUserIn(BaseModel):
    telegram_id: int = Field(gt=0)
    first_name: str = Field(max_length=100)
    locale_hint: Locale = Locale.UZ


class BotUserOut(BaseModel):
    user_id: uuid.UUID
    display_name: str
    locale: Locale
    created: bool  # true on the very first /start — the bot then shows the language picker
