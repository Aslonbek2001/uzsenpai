"""Error codes of the auth module (translated by clients in uz/ru/en/ja)."""

from app.shared.errors import AppError, Forbidden, NotFound


class Unauthorized(AppError):
    status = 401


class InvalidCredentials(Unauthorized):
    """Wrong email or password — deliberately the same code for both (no account enumeration)."""


class InvalidCode(AppError):
    """Verification / reset code wrong, expired or used up."""


class InvalidRefreshToken(Unauthorized):
    pass


class RefreshRace(AppError):
    """Another tab rotated this token a moment ago — retry once with the new cookie."""

    status = 409


class InvalidTelegramData(Unauthorized):
    pass


class AccountDeleted(Forbidden):
    pass


class SessionNotFound(NotFound):
    pass
