"""Google sign-in and linking: start (state + PKCE + nonce in Redis) → callback (verify, then sign in or link)."""

import secrets
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis
from app.modules.auth.domain.enums import AuthProvider, OAuthMode
from app.modules.auth.domain.exceptions import EmailRegistered, SignInFailed
from app.modules.auth.domain.rules import normalize_email
from app.modules.auth.providers.email import CodeSender
from app.modules.auth.providers.google import GoogleOAuth, GoogleProfile, pkce_pair
from app.modules.auth.repositories import IdentityRepository, OAuthStateStore
from app.modules.auth.services.link_service import LinkService
from app.modules.auth.services.session_service import ClientInfo, IssuedTokens, SessionService
from app.modules.users.public import UsersFacade
from app.shared.i18n import Locale


@dataclass(frozen=True)
class GoogleResult:
    mode: OAuthMode
    tokens: IssuedTokens | None  # set for LOGIN


class GoogleAuthService:
    def __init__(self, session: AsyncSession, google: GoogleOAuth, sender: CodeSender) -> None:
        self.google = google
        self.states = OAuthStateStore(redis)
        self.identities = IdentityRepository(session)
        self.users = UsersFacade(session)
        self.sessions = SessionService(session)
        self.links = LinkService(session, sender)

    async def start(self, mode: OAuthMode, locale: Locale, user_id: uuid.UUID | None = None) -> str:
        verifier, challenge = pkce_pair()
        nonce = secrets.token_urlsafe(32)
        state = await self.states.create(
            {
                "mode": mode.value,
                "user_id": str(user_id) if user_id else None,
                "code_verifier": verifier,
                "nonce": nonce,
                "locale": locale.value,
            }
        )
        return self.google.authorization_url(state=state, code_challenge=challenge, nonce=nonce)

    async def callback(self, code: str, state: str, client: ClientInfo) -> GoogleResult:
        saved = await self.states.take(state)
        if saved is None:
            raise SignInFailed("auth.sign_in_failed")  # unknown, reused or expired state (CSRF / replay)
        profile = await self.google.exchange(code=code, code_verifier=saved["code_verifier"], nonce=saved["nonce"])
        mode = OAuthMode(saved["mode"])
        if mode == OAuthMode.LINK:
            email = normalize_email(profile.email) if profile.email and profile.email_verified else None
            await self.links.link(uuid.UUID(saved["user_id"]), AuthProvider.GOOGLE, profile.sub, email=email)
            return GoogleResult(mode, None)
        return GoogleResult(mode, await self._sign_in(profile, Locale(saved["locale"]), client))

    async def _sign_in(self, profile: GoogleProfile, locale: Locale, client: ClientInfo) -> IssuedTokens:
        identity = await self.identities.get(AuthProvider.GOOGLE, profile.sub)
        if identity is not None:
            user = await self.users.get(identity.user_id)
            if user is None:
                raise SignInFailed("auth.sign_in_failed")
            await self.identities.touch_login(identity)
            return await self.sessions.start(user, client)
        email = normalize_email(profile.email) if profile.email and profile.email_verified else None
        if email and await self.identities.get(AuthProvider.EMAIL, email) is not None:
            # No silent merge (owner's rule: linking is manual). Sign in with the password, then link Google.
            raise EmailRegistered("auth.email_registered")
        name = profile.name or (email.split("@")[0] if email else "User")
        user = await self.users.create(display_name=name, locale=locale)
        await self.identities.add(user_id=user.id, provider=AuthProvider.GOOGLE, subject=profile.sub, email=email)
        return await self.sessions.start(user, client)
