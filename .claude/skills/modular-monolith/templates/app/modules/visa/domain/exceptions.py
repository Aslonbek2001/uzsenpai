"""Error codes of the visa module (translated by clients in uz/ru/en/ja)."""

from app.shared.errors import AppError, NotFound


class VisaStatusNotSet(NotFound):
    pass


class ExpiryInPast(AppError):
    status = 422
