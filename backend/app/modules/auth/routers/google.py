"""/api/v1/auth/google/* — Google sign-in and linking (authorization code + PKCE).

The client calls /start (or /link) for a URL and navigates the browser there; Google sends the browser back to
/callback, which sets the refresh cookie (sign-in) and redirects to the website with `result` or `error`.
The website then calls /auth/refresh to get an access token — no token ever travels in a URL.
"""

from urllib.parse import urlencode

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.modules.auth.domain.enums import OAuthMode
from app.modules.auth.public import CurrentUserDep
from app.modules.auth.routers.cookies import set_refresh_cookie
from app.modules.auth.routers.deps import Client, GoogleAuth, RequestLocale
from app.modules.auth.schemas import OAuthStartOut
from app.shared.errors import AppError

router = APIRouter(prefix="/google")

WEB_DONE_PATH = "/auth/google/done"


def _to_web(**params: str) -> RedirectResponse:
    return RedirectResponse(f"{settings.public_web_url}{WEB_DONE_PATH}?{urlencode(params)}", status_code=303)


@router.post("/start", response_model=OAuthStartOut)
async def start_sign_in(google: GoogleAuth, locale: RequestLocale) -> OAuthStartOut:
    return OAuthStartOut(authorization_url=await google.start(OAuthMode.LOGIN, locale))


@router.post("/link", response_model=OAuthStartOut)
async def start_link(user: CurrentUserDep, google: GoogleAuth, locale: RequestLocale) -> OAuthStartOut:
    return OAuthStartOut(authorization_url=await google.start(OAuthMode.LINK, locale, user.id))


@router.get("/callback", include_in_schema=False)
async def callback(
    google: GoogleAuth, client: Client, code: str = "", state: str = "", error: str = ""
) -> RedirectResponse:
    if error or not code or not state:  # the user pressed "cancel" on Google's page, or a broken request
        return _to_web(error="auth.sign_in_cancelled")
    try:
        result = await google.callback(code, state, client)
    except AppError as exc:  # nothing was written on these paths, so answering normally is safe
        return _to_web(error=exc.code)
    if result.tokens is None:
        return _to_web(result="linked")
    response = _to_web(result="signed_in")
    set_refresh_cookie(response, result.tokens)
    return response
