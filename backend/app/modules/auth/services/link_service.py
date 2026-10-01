"""Linking sign-in methods to the signed-in account (manual only — never merged automatically) and unlinking."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.domain.enums import AuthProvider, CodePurpose
from app.modules.auth.domain.exceptions import IdentityInUse, IdentityNotFound, LastIdentity, ProviderAlreadyLinked
from app.modules.auth.domain.rules import normalize_email
from app.modules.auth.providers.email import CodeSender
from app.modules.auth.repositories import IdentityRepository
from app.modules.auth.schemas import IdentityOut, LinkEmailConfirmIn, LinkEmailStartIn, TelegramLoginIn
from app.modules.auth.services.email_auth_service import EmailAuthService
from app.modules.auth.services.passwords import hash_password
from app.modules.auth.services.session_service import ClientInfo
from app.modules.auth.services.telegram_auth_service import TelegramAuthService
from app.shared.i18n import Locale


class LinkService:
    def __init__(self, session: AsyncSession, sender: CodeSender) -> None:
        self.identities = IdentityRepository(session)
        self.email = EmailAuthService(session, sender)

    async def list(self, user_id: uuid.UUID) -> list[IdentityOut]:
        return [IdentityOut.model_validate(i) for i in await self.identities.list_for_user(user_id)]

    async def link(self, user_id: uuid.UUID, provider: AuthProvider, subject: str, email: str | None = None) -> None:
        """Shared by Telegram / Google / email linking. Idempotent for the same account."""
        owner = await self.identities.get(provider, subject)
        if owner is not None:
            if owner.user_id == user_id:
                return
            raise IdentityInUse("auth.identity_in_use")
        if await self.identities.get_for_user(user_id, provider) is not None:
            raise ProviderAlreadyLinked("auth.provider_already_linked")
        await self.identities.add(user_id=user_id, provider=provider, subject=subject, email=email)

    async def link_telegram(self, user_id: uuid.UUID, data: TelegramLoginIn) -> None:
        TelegramAuthService.verify(data)
        await self.link(user_id, AuthProvider.TELEGRAM, str(data.id))

    async def start_email(self, user_id: uuid.UUID, data: LinkEmailStartIn, locale: Locale, client: ClientInfo) -> None:
        if await self.identities.get_for_user(user_id, AuthProvider.EMAIL) is not None:
            raise ProviderAlreadyLinked("auth.provider_already_linked")
        email = normalize_email(data.email)
        await self.email.limit_code_requests(email, client)
        await self.email.send_code(CodePurpose.LINK_EMAIL, email, locale)

    async def confirm_email(self, user_id: uuid.UUID, data: LinkEmailConfirmIn, client: ClientInfo) -> None:
        email = normalize_email(data.email)
        await self.email.redeem(CodePurpose.LINK_EMAIL, email, data.code, client)
        await self.link(user_id, AuthProvider.EMAIL, email, email=email)
        identity = await self.identities.get(AuthProvider.EMAIL, email)
        if identity is not None and identity.password_hash is None:
            await self.identities.set_password(identity, await hash_password(data.password))

    async def unlink(self, user_id: uuid.UUID, provider: AuthProvider) -> None:
        identity = await self.identities.get_for_user(user_id, provider)
        if identity is None:
            raise IdentityNotFound("auth.identity_not_found")
        if await self.identities.count_for_user(user_id) <= 1:
            raise LastIdentity("auth.last_identity")
        await self.identities.remove(identity)
