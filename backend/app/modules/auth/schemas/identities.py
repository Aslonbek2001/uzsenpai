"""API contract for linked sign-in methods and Google start."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.modules.auth.domain.enums import AuthProvider
from app.modules.auth.schemas.email import Code, Password


class IdentityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: AuthProvider
    email: str | None  # shown for email / Google; Telegram shows just "Telegram"
    created_at: datetime
    last_login_at: datetime | None


class LinkEmailStartIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr


class LinkEmailConfirmIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    code: Code
    password: Password


class OAuthStartOut(BaseModel):
    authorization_url: str  # the client navigates the browser here
