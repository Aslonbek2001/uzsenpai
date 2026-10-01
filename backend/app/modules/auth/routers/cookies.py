"""The refresh token lives only in this httpOnly cookie, scoped to /api/v1/auth (never sent to other routes)."""

from fastapi import Response

from app.core.config import settings
from app.modules.auth.schemas import TokenOut
from app.modules.auth.services import IssuedTokens

REFRESH_COOKIE = "uzs_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def tokens_response(response: Response, tokens: IssuedTokens) -> TokenOut:
    response.set_cookie(
        REFRESH_COOKIE,
        tokens.refresh_token,
        expires=tokens.refresh_expires_at,
        path=REFRESH_COOKIE_PATH,
        httponly=True,  # JavaScript can't read it → XSS can't steal it
        secure=settings.refresh_cookie_secure,
        samesite="lax",  # not sent on cross-site POSTs → no CSRF on /refresh
    )
    response.headers["Cache-Control"] = "no-store"
    return TokenOut(access_token=tokens.access_token, expires_in=tokens.expires_in)


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, secure=settings.refresh_cookie_secure, httponly=True, samesite="lax"
    )
