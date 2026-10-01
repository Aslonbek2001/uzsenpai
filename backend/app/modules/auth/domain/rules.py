"""Pure rules for authentication — no I/O."""

from datetime import timedelta

ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=30)
REFRESH_TOKEN_BYTES = 32  # 256-bit random token; only its SHA-256 is stored

VERIFICATION_CODE_TTL = timedelta(minutes=15)  # email confirmation / password reset codes (Redis)
VERIFICATION_CODE_MAX_ATTEMPTS = 5


def normalize_email(email: str) -> str:
    """Emails are unique case-insensitively: stored and compared lower-cased and trimmed."""
    return email.strip().lower()
