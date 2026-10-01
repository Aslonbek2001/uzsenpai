"""Google sign-in: OAuth 2.0 authorization code flow with PKCE + OpenID Connect ID token (ADR 0007).

Docs: https://developers.google.com/identity/openid-connect/openid-connect (checked 2026-10).
We trust only the ID token's verified claims: signature (Google JWKS), audience = our client id, issuer,
expiry, and the nonce we generated. The identity key is `sub` — never the email (emails can change).
"""

import asyncio
import base64
import hashlib
import secrets
from typing import Protocol
from urllib.parse import urlencode

import httpx
import jwt
from pydantic import BaseModel

from app.modules.auth.domain.exceptions import SignInFailed

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105 — an endpoint URL, not a secret
JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
ISSUERS = ["https://accounts.google.com", "accounts.google.com"]

_jwks = jwt.PyJWKClient(JWKS_URL, cache_keys=True, lifespan=3600)


class GoogleProfile(BaseModel):
    sub: str
    email: str | None
    email_verified: bool
    name: str | None


class GoogleOAuth(Protocol):
    def authorization_url(self, *, state: str, code_challenge: str, nonce: str) -> str: ...

    async def exchange(self, *, code: str, code_verifier: str, nonce: str) -> GoogleProfile: ...


def pkce_pair() -> tuple[str, str]:
    """(code_verifier, S256 code_challenge)."""
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


class GoogleOAuthClient:
    def __init__(self, *, client_id: str, client_secret: str, redirect_uri: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def authorization_url(self, *, state: str, code_challenge: str, nonce: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
        return f"{AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange(self, *, code: str, code_verifier: str, nonce: str) -> GoogleProfile:
        try:
            async with httpx.AsyncClient(timeout=10) as http:
                response = await http.post(
                    TOKEN_URL,
                    data={
                        "code": code,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "redirect_uri": self.redirect_uri,
                        "grant_type": "authorization_code",
                        "code_verifier": code_verifier,
                    },
                )
            response.raise_for_status()
            id_token = response.json()["id_token"]
            signing_key = await asyncio.to_thread(_jwks.get_signing_key_from_jwt, id_token)  # cached, may fetch
            claims = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=ISSUERS,
                options={"require": ["exp", "iat", "sub", "aud", "iss"]},
            )
        except (httpx.HTTPError, KeyError, ValueError, jwt.PyJWTError) as exc:
            raise SignInFailed("auth.sign_in_failed") from exc
        if not secrets.compare_digest(str(claims.get("nonce", "")), nonce):
            raise SignInFailed("auth.sign_in_failed")
        return GoogleProfile(
            sub=str(claims["sub"]),
            email=claims.get("email"),
            email_verified=bool(claims.get("email_verified")),
            name=claims.get("name"),
        )
