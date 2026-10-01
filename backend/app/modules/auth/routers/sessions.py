"""/api/v1/auth/{refresh,logout,logout-all,sessions} — the refresh-token cookie and the "Devices" list."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Cookie, Response, status
from fastapi.responses import JSONResponse

from app.modules.auth.domain.exceptions import InvalidRefreshToken
from app.modules.auth.public import CurrentUserDep
from app.modules.auth.routers.cookies import REFRESH_COOKIE, clear_refresh_cookie, tokens_response
from app.modules.auth.routers.deps import Client, Sessions
from app.modules.auth.schemas import SessionOut, TokenOut

router = APIRouter()

RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE)]


@router.post("/refresh", response_model=TokenOut)
async def refresh(
    sessions: Sessions, client: Client, response: Response, token: RefreshCookie = None
) -> TokenOut | JSONResponse:
    """New access token + rotated refresh cookie. 409 `auth.refresh_race` → retry once (another tab won)."""
    if not token:
        raise InvalidRefreshToken("auth.invalid_refresh")
    tokens = await sessions.refresh(token, client)
    if tokens is None:  # rejected, but the revocation must commit → answer without raising
        rejected = JSONResponse(status_code=401, content={"error": {"code": "auth.invalid_refresh", "params": {}}})
        clear_refresh_cookie(rejected)
        return rejected
    return tokens_response(response, tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(sessions: Sessions, response: Response, token: RefreshCookie = None) -> None:
    if token:
        await sessions.logout(token)
    clear_refresh_cookie(response)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(user: CurrentUserDep, sessions: Sessions, response: Response) -> None:
    await sessions.logout_all(user.id)
    clear_refresh_cookie(response)


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(user: CurrentUserDep, sessions: Sessions) -> list[SessionOut]:
    return await sessions.devices(user.id, user.session_family_id)


@router.delete("/sessions/{family_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(family_id: uuid.UUID, user: CurrentUserDep, sessions: Sessions) -> None:
    await sessions.revoke_device(user.id, family_id)
