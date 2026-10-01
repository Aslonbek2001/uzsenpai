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


class IdentityInUse(AppError):
    """This Telegram / email / Google account already belongs to another user."""

    status = 409


class ProviderAlreadyLinked(AppError):
    status = 409


class LastIdentity(AppError):
    """Unlinking it would leave the account with no way to sign in."""

    status = 409


class EmailRegistered(AppError):
    """Google sign-in with an email that has a password account: sign in with the password, then link Google."""

    status = 409


class SignInFailed(Unauthorized):
    """The OAuth provider refused, or its answer didn't verify (state, nonce, signature, audience)."""


class ProviderUnavailable(AppError):
    status = 503


class IdentityNotFound(NotFound):
    pass
