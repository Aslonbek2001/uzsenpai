"""Short-lived JWT access tokens (HS256, PyJWT — ADR 0007). Stateless: verified without a database call."""

import uuid
from datetime import UTC, datetime

import jwt
from pydantic import BaseModel

from app.core.config import settings
from app.modules.auth.domain.rules import ACCESS_TOKEN_TTL
from app.modules.users.public import UserRole

_ALGORITHM = "HS256"
_ISSUER = "uzsenpai-api"


class AccessClaims(BaseModel):
    user_id: uuid.UUID
    role: UserRole
    family_id: uuid.UUID  # the refresh-token family (device) this access token belongs to


def issue_access_token(user_id: uuid.UUID, role: UserRole, family_id: uuid.UUID) -> tuple[str, int]:
    now = datetime.now(UTC)
    payload = {
        "iss": _ISSUER,
        "sub": str(user_id),
        "role": role.value,
        "sid": str(family_id),
        "typ": "access",
        "iat": now,
        "exp": now + ACCESS_TOKEN_TTL,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM), int(ACCESS_TOKEN_TTL.total_seconds())


def decode_access_token(token: str) -> AccessClaims | None:
    """Claims of a valid, unexpired access token; None for anything else (expired, forged, wrong type)."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[_ALGORITHM],  # pinned: never let the token choose its algorithm
            issuer=_ISSUER,
            options={"require": ["exp", "iat", "sub", "iss"]},
        )
        if payload.get("typ") != "access":
            return None
        return AccessClaims(user_id=payload["sub"], role=payload["role"], family_id=payload["sid"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
