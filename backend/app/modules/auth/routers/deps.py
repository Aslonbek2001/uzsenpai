"""Dependency wiring for auth routers — session, Redis code store, code sender, client info, bot guard."""

from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.db import SessionDep
from app.modules.auth.domain.exceptions import ProviderUnavailable
from app.modules.auth.providers.email import CodeSender, LogCodeSender
from app.modules.auth.providers.google import GoogleOAuth, GoogleOAuthClient
from app.modules.auth.services import (
    ClientInfo,
    EmailAuthService,
    GoogleAuthService,
    LinkService,
    SessionService,
    TelegramAuthService,
    is_bot_token,
)
from app.shared.i18n import Locale, locale_from_request


def get_code_sender() -> CodeSender:
    """Overridden in tests. A real email sender arrives with the notifications module."""
    if not settings.is_local:
        raise RuntimeError("no email sender configured outside local/test — wire the notifications sender")
    return LogCodeSender()


GOOGLE_CALLBACK_PATH = "/api/v1/auth/google/callback"


def get_google() -> GoogleOAuth:
    """Overridden in tests. 503 `auth.provider_unavailable` until GOOGLE_CLIENT_ID/SECRET are set."""
    if not settings.google_enabled:
        raise ProviderUnavailable("auth.provider_unavailable")
    return GoogleOAuthClient(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=f"{settings.public_api_url}{GOOGLE_CALLBACK_PATH}",
    )


def get_client_info(request: Request) -> ClientInfo:
    ip: IPv4Address | IPv6Address | None = None
    if request.client is not None:
        try:
            ip = ip_address(request.client.host)
        except ValueError:
            ip = None  # e.g. the test client's "testclient"
    return ClientInfo(user_agent=request.headers.get("user-agent"), ip=ip)


def get_locale(request: Request) -> Locale:
    return locale_from_request(request)


def get_email_auth(session: SessionDep, sender: Annotated[CodeSender, Depends(get_code_sender)]) -> EmailAuthService:
    return EmailAuthService(session, sender)


def get_link_service(session: SessionDep, sender: Annotated[CodeSender, Depends(get_code_sender)]) -> LinkService:
    return LinkService(session, sender)


def get_google_auth(
    session: SessionDep,
    google: Annotated[GoogleOAuth, Depends(get_google)],
    sender: Annotated[CodeSender, Depends(get_code_sender)],
) -> GoogleAuthService:
    return GoogleAuthService(session, google, sender)


def get_session_service(session: SessionDep) -> SessionService:
    return SessionService(session)


def get_telegram_auth(session: SessionDep) -> TelegramAuthService:
    return TelegramAuthService(session)


async def require_bot(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(HTTPBearer(auto_error=False))],
) -> None:
    if credentials is None or not is_bot_token(credentials.credentials):
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Bearer"})


Client = Annotated[ClientInfo, Depends(get_client_info)]
RequestLocale = Annotated[Locale, Depends(get_locale)]
EmailAuth = Annotated[EmailAuthService, Depends(get_email_auth)]
Sessions = Annotated[SessionService, Depends(get_session_service)]
TelegramAuth = Annotated[TelegramAuthService, Depends(get_telegram_auth)]
Links = Annotated[LinkService, Depends(get_link_service)]
GoogleAuth = Annotated[GoogleAuthService, Depends(get_google_auth)]
