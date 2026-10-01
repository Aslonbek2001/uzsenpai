"""The bot's service token (BOT_SERVICE_TOKEN) — compared in constant time."""

import hmac

from app.core.config import settings


def is_bot_token(token: str) -> bool:
    expected = settings.bot_service_token.encode()
    return bool(expected) and hmac.compare_digest(token.encode(), expected)  # bytes: any header text is safe
