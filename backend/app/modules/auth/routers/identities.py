"""/api/v1/auth/identities, /link/* — sign-in methods of the signed-in account (manual linking only)."""

from fastapi import APIRouter, status

from app.modules.auth.domain.enums import AuthProvider
from app.modules.auth.public import CurrentUserDep
from app.modules.auth.routers.deps import Client, Links, RequestLocale
from app.modules.auth.schemas import IdentityOut, LinkEmailConfirmIn, LinkEmailStartIn, TelegramLoginIn

router = APIRouter()


@router.get("/identities", response_model=list[IdentityOut])
async def list_identities(user: CurrentUserDep, links: Links) -> list[IdentityOut]:
    return await links.list(user.id)


@router.delete("/identities/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink(provider: AuthProvider, user: CurrentUserDep, links: Links) -> None:
    """409 `auth.last_identity` when it's the only way left to sign in."""
    await links.unlink(user.id, provider)


@router.post("/link/telegram", status_code=status.HTTP_204_NO_CONTENT)
async def link_telegram(data: TelegramLoginIn, user: CurrentUserDep, links: Links) -> None:
    await links.link_telegram(user.id, data)


@router.post("/link/email/start", status_code=status.HTTP_202_ACCEPTED)
async def link_email_start(
    data: LinkEmailStartIn, user: CurrentUserDep, links: Links, locale: RequestLocale, client: Client
) -> None:
    await links.start_email(user.id, data, locale, client)


@router.post("/link/email/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def link_email_confirm(data: LinkEmailConfirmIn, user: CurrentUserDep, links: Links, client: Client) -> None:
    await links.confirm_email(user.id, data, client)
