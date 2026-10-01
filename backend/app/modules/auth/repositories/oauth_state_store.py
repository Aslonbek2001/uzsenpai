"""OAuth `state` → what to do when Google redirects back (PKCE verifier, nonce, login/link). Single use, 10 min."""

import json
import secrets
from typing import Any

from redis.asyncio import Redis

from app.modules.auth.domain.rules import OAUTH_STATE_TTL


class OAuthStateStore:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def create(self, data: dict[str, Any]) -> str:
        state = secrets.token_urlsafe(32)
        await self.redis.set(f"auth:oauth:{state}", json.dumps(data), ex=int(OAUTH_STATE_TTL.total_seconds()))
        return state

    async def take(self, state: str) -> dict[str, Any] | None:
        raw = await self.redis.getdel(f"auth:oauth:{state}")  # atomic: a state works exactly once
        return None if raw is None else dict(json.loads(raw))
