"""Stable codes stored in the database."""

from enum import StrEnum


class AuthProvider(StrEnum):
    TELEGRAM = "telegram"  # subject = Telegram user id
    EMAIL = "email"  # subject = lower-cased email; the only provider with a password
    GOOGLE = "google"  # subject = Google account id ("sub" claim), never the email (emails can change)


class SessionRevokeReason(StrEnum):
    LOGOUT = "logout"
    LOGOUT_ALL = "logout_all"
    ROTATED = "rotated"  # replaced by a new refresh token — presenting it again means it was stolen
    REUSE_DETECTED = "reuse_detected"  # a rotated token was reused → the whole family is revoked
    PASSWORD_CHANGED = "password_changed"  # noqa: S105 — a status code, not a secret
    ACCOUNT_DELETED = "account_deleted"
