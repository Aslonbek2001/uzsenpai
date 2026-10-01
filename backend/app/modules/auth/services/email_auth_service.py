"""Email + password: sign-up with a code, sign-in, password reset.

Anti-enumeration: sign-up and "forgot password" always answer the same way whether the email exists or not,
and sign-in uses one error for "no such email" and "wrong password" (with equal timing). The real email sender
must enqueue delivery (Taskiq) instead of calling the provider inline, so response times don't differ either.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import rate_limit
from app.core.redis import redis
from app.modules.auth.domain.enums import AuthProvider, CodePurpose, SessionRevokeReason
from app.modules.auth.domain.exceptions import AccountDeleted, InvalidCode, InvalidCredentials
from app.modules.auth.domain.rules import (
    CODE_FAILURES_PER_EMAIL,
    CODE_FAILURES_PER_IP,
    CODE_REQUESTS_PER_EMAIL,
    CODE_REQUESTS_PER_IP,
    LOGIN_FAILURES_PER_EMAIL,
    LOGIN_FAILURES_PER_IP,
    new_verification_code,
    normalize_email,
)
from app.modules.auth.providers.email import CodeSender
from app.modules.auth.repositories import CodeStore, IdentityRepository
from app.modules.auth.schemas import ForgotPasswordIn, LoginIn, RegisterIn, ResetPasswordIn, VerifyEmailIn
from app.modules.auth.services.passwords import hash_password, verify_password
from app.modules.auth.services.session_service import ClientInfo, IssuedTokens, SessionService
from app.modules.users.public import UsersFacade
from app.shared.i18n import Locale


class EmailAuthService:
    def __init__(self, session: AsyncSession, sender: CodeSender, codes: CodeStore | None = None) -> None:
        self.identities = IdentityRepository(session)
        self.users = UsersFacade(session)
        self.sessions = SessionService(session)
        self.codes = codes or CodeStore(redis)
        self.sender = sender

    async def register(self, data: RegisterIn, locale: Locale, client: ClientInfo) -> None:
        email = normalize_email(data.email)
        await self.limit_code_requests(email, client)
        if await self.identities.get(AuthProvider.EMAIL, email) is not None:
            return  # already registered: same answer as success (the owner can use "forgot password")
        await self.send_code(CodePurpose.SIGNUP, email, locale)

    async def verify_email(self, data: VerifyEmailIn, client: ClientInfo) -> IssuedTokens:
        """The code proves the mailbox: only now are the user and the identity created, with the password the
        code holder chose."""
        email = normalize_email(data.email)
        payload = await self.redeem(CodePurpose.SIGNUP, email, data.code, client)
        if await self.identities.get(AuthProvider.EMAIL, email) is not None:
            raise InvalidCode("auth.invalid_code")
        user = await self.users.create(display_name=data.display_name, locale=Locale(payload["locale"]))
        await self.identities.add(
            user_id=user.id,
            provider=AuthProvider.EMAIL,
            subject=email,
            email=email,
            password_hash=await hash_password(data.password),
        )
        return await self.sessions.start(user, client)

    async def login(self, data: LoginIn, client: ClientInfo) -> IssuedTokens:
        email = normalize_email(data.email)
        email_key, ip_key = f"login-fail:email:{email}", f"login-fail:ip:{client.ip}"
        await rate_limit.ensure_allowed(email_key, limit=LOGIN_FAILURES_PER_EMAIL[0])
        if client.ip is not None:
            await rate_limit.ensure_allowed(ip_key, limit=LOGIN_FAILURES_PER_IP[0])
        identity = await self.identities.get(AuthProvider.EMAIL, email)
        matches, needs_rehash = await verify_password(identity.password_hash if identity else None, data.password)
        if identity is None or not matches:
            await rate_limit.hit(email_key, limit=LOGIN_FAILURES_PER_EMAIL[0], window=LOGIN_FAILURES_PER_EMAIL[1])
            if client.ip is not None:
                await rate_limit.hit(ip_key, limit=LOGIN_FAILURES_PER_IP[0], window=LOGIN_FAILURES_PER_IP[1])
            raise InvalidCredentials("auth.invalid_credentials")
        user = await self.users.get(identity.user_id)
        if user is None or not user.can_sign_in:
            raise AccountDeleted("auth.account_deleted")
        if needs_rehash:
            await self.identities.set_password(identity, await hash_password(data.password))
        await self.identities.touch_login(identity)
        return await self.sessions.start(user, client)

    async def forgot_password(self, data: ForgotPasswordIn, locale: Locale, client: ClientInfo) -> None:
        email = normalize_email(data.email)
        await self.limit_code_requests(email, client)
        if await self.identities.get(AuthProvider.EMAIL, email) is None:
            return  # same answer as success
        await self.send_code(CodePurpose.PASSWORD_RESET, email, locale)

    async def reset_password(self, data: ResetPasswordIn, client: ClientInfo) -> None:
        """New password + every device signed out (the old password may be known to someone else)."""
        email = normalize_email(data.email)
        await self.redeem(CodePurpose.PASSWORD_RESET, email, data.code, client)
        identity = await self.identities.get(AuthProvider.EMAIL, email)
        if identity is None:
            raise InvalidCode("auth.invalid_code")
        await self.identities.set_password(identity, await hash_password(data.new_password))
        await self.sessions.logout_all(identity.user_id, SessionRevokeReason.PASSWORD_CHANGED)

    async def redeem(self, purpose: CodePurpose, email: str, code: str, client: ClientInfo) -> dict[str, str]:
        """Consume a code; wrong codes count against the email (per day) and the IP (per 15 min)."""
        email_key, ip_key = f"code-fail:email:{email}", f"code-fail:ip:{client.ip}"
        await rate_limit.ensure_allowed(email_key, limit=CODE_FAILURES_PER_EMAIL[0])
        if client.ip is not None:
            await rate_limit.ensure_allowed(ip_key, limit=CODE_FAILURES_PER_IP[0])
        payload = await self.codes.take(purpose, email, code)
        if payload is None:
            await rate_limit.hit(email_key, limit=CODE_FAILURES_PER_EMAIL[0], window=CODE_FAILURES_PER_EMAIL[1])
            if client.ip is not None:
                await rate_limit.hit(ip_key, limit=CODE_FAILURES_PER_IP[0], window=CODE_FAILURES_PER_IP[1])
            raise InvalidCode("auth.invalid_code")
        return payload

    async def limit_code_requests(self, email: str, client: ClientInfo) -> None:
        limit, window = CODE_REQUESTS_PER_EMAIL
        await rate_limit.hit(f"code-request:email:{email}", limit=limit, window=window)
        if client.ip is not None:  # unknown IP (proxy misconfigured) must not become one shared bucket
            limit, window = CODE_REQUESTS_PER_IP
            await rate_limit.hit(f"code-request:ip:{client.ip}", limit=limit, window=window)

    async def send_code(self, purpose: CodePurpose, email: str, locale: Locale) -> None:
        code = new_verification_code()
        await self.codes.put(purpose, email, code, {"locale": locale.value})
        await self.sender.send(email=email, code=code, purpose=purpose, locale=locale)
