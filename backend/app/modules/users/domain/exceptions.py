"""Error codes of the users module (translated by clients in uz/ru/en/ja)."""

from app.shared.errors import AppError, NotFound


class UserNotFound(NotFound):
    pass


class NotPendingDeletion(AppError):
    status = 409
