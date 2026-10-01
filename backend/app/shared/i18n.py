"""app/shared/i18n.py — the four languages and translatable content."""

from enum import StrEnum

from fastapi import Request
from pydantic import BaseModel, model_validator


class Locale(StrEnum):
    UZ = "uz"
    RU = "ru"
    EN = "en"
    JA = "ja"


DEFAULT_LOCALE = Locale.UZ


class LocalizedText(BaseModel):
    """Stored as JSONB. uz is required; others may be missing until translated."""

    uz: str
    ru: str | None = None
    en: str | None = None
    ja: str | None = None

    @model_validator(mode="after")
    def _uz_not_empty(self) -> "LocalizedText":
        if not self.uz.strip():
            raise ValueError("uz text is required")
        return self

    def resolve(self, locale: Locale) -> tuple[str, Locale]:
        """Text for the locale and the locale actually used (falls back to uz)."""
        value = getattr(self, locale.value)
        return (value, locale) if value else (self.uz, DEFAULT_LOCALE)


def locale_from_request(request: Request, user_locale: str | None = None) -> Locale:
    """User profile wins; else the first supported Accept-Language tag; else uz."""
    if user_locale is not None and user_locale in Locale._value2member_map_:
        return Locale(user_locale)
    header = request.headers.get("accept-language", "")
    for part in header.split(","):
        tag = part.split(";")[0].strip().lower()[:2]
        if tag in Locale._value2member_map_:
            return Locale(tag)
    return DEFAULT_LOCALE
