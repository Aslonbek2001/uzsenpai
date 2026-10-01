"""One-time email codes in Redis: 15-minute TTL, at most 5 wrong attempts, single use.

Codes carry no secrets chosen by the requester: whoever holds the code (= owns the mailbox) supplies the
password when redeeming it. A new request for the same email replaces the pending code.
"""

import hmac
import json
from typing import Any, cast

from redis.asyncio import Redis

from app.modules.auth.domain.enums import CodePurpose
from app.modules.auth.domain.rules import VERIFICATION_CODE_MAX_ATTEMPTS, VERIFICATION_CODE_TTL, hash_token


def _key(purpose: CodePurpose, email: str) -> str:
    return f"auth:code:{purpose}:{email}"


class CodeStore:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def put(self, purpose: CodePurpose, email: str, code: str, payload: dict[str, Any]) -> None:
        key = _key(purpose, email)
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.delete(key)
            pipe.hset(key, mapping={"code": hash_token(code).hex(), "attempts": 0, "payload": json.dumps(payload)})
            pipe.expire(key, int(VERIFICATION_CODE_TTL.total_seconds()))
            await pipe.execute()

    async def take(self, purpose: CodePurpose, email: str, code: str) -> dict[str, Any] | None:
        """Payload if the code is right (and consume it); None if wrong/expired (wrong ones count attempts)."""
        key = _key(purpose, email)
        entry = cast(dict[str, str], await self.redis.hgetall(key))  # client uses decode_responses=True
        if "code" not in entry:
            return None
        if hmac.compare_digest(entry["code"], hash_token(code).hex()):
            # delete() returns 1 for exactly one of two concurrent correct submissions
            consumed = await self.redis.delete(key)
            return json.loads(entry["payload"]) if consumed else None
        attempts = await self.redis.hincrby(key, "attempts", 1)
        # >= max → burn it. TTL -1 → the right code consumed the key concurrently and HINCRBY re-created a stub.
        if attempts >= VERIFICATION_CODE_MAX_ATTEMPTS or await self.redis.ttl(key) == -1:
            await self.redis.delete(key)
        return None
