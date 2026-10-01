"""Token response shared by every sign-in method. The refresh token is never in a body — only an httpOnly cookie."""

from typing import Literal

from pydantic import BaseModel


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 — the OAuth token type, not a secret
    expires_in: int  # seconds
