"""Pure rules for authentication — no I/O."""

import hashlib
import secrets
from datetime import timedelta

ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=30)
REFRESH_TOKEN_BYTES = 32  # 256-bit random token; only its SHA-256 is stored
# Two tabs refreshing at once: the loser presents a token rotated a moment ago. Inside this window it's a race
# (answer 409, the client retries with the new cookie), after it it's theft (revoke the whole family).
REFRESH_RACE_GRACE = timedelta(seconds=15)

VERIFICATION_CODE_TTL = timedelta(minutes=15)  # email confirmation / password reset codes (Redis)
VERIFICATION_CODE_MAX_ATTEMPTS = 5
VERIFICATION_CODE_DIGITS = 6

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128  # bounds argon2 work per request

OAUTH_STATE_TTL = timedelta(minutes=10)
SESSION_PURGE_EXPIRED_AFTER = timedelta(days=7)  # expired refresh rows kept a week (support/debugging)
SESSION_PURGE_REVOKED_AFTER = timedelta(days=30)  # revoked rows kept a month (reuse detection, audit)

TELEGRAM_AUTH_MAX_AGE = timedelta(minutes=10)  # Login Widget data older than this is refused (limits replay)

# Brute-force limits: (attempts, window). Login and code checks count FAILURES only.
LOGIN_FAILURES_PER_EMAIL = (10, timedelta(minutes=15))
LOGIN_FAILURES_PER_IP = (50, timedelta(minutes=15))
CODE_REQUESTS_PER_EMAIL = (5, timedelta(hours=1))  # sign-up / password-reset emails sent
CODE_REQUESTS_PER_IP = (20, timedelta(hours=1))
CODE_FAILURES_PER_IP = (30, timedelta(minutes=15))
# Caps guessing across many re-sent codes: 20 wrong codes per email per day, then that email's codes are locked
CODE_FAILURES_PER_EMAIL = (20, timedelta(days=1))


def normalize_email(email: str) -> str:
    """Emails are unique case-insensitively: stored and compared lower-cased and trimmed."""
    return email.strip().lower()


def new_verification_code() -> str:
    return f"{secrets.randbelow(10**VERIFICATION_CODE_DIGITS):0{VERIFICATION_CODE_DIGITS}d}"


def new_refresh_token() -> str:
    return secrets.token_urlsafe(REFRESH_TOKEN_BYTES)


def hash_token(token: str) -> bytes:
    """Refresh tokens and codes are high-entropy or short-lived: SHA-256 is enough (no slow hash needed)."""
    return hashlib.sha256(token.encode()).digest()
