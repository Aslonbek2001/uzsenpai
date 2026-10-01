"""app/core/rate_limit.py — fixed-window counters in Redis for brute-force protection (login, codes).

Typical use: `ensure_allowed` before the check, `hit` only when the attempt FAILED — so an attacker can't lock
a victim out with attempts that never had a chance, and successful users never burn their budget.
"""

from datetime import timedelta

from app.core.redis import redis
from app.shared.errors import AppError


class RateLimited(AppError):
    status = 429


def _key(key: str) -> str:
    return f"rl:{key}"


async def ensure_allowed(key: str, *, limit: int) -> None:
    """Raise `common.rate_limited` if `key` already used up its `limit` in the current window."""
    count = await redis.get(_key(key))
    if count is not None and int(count) >= limit:
        ttl = await redis.ttl(_key(key))
        raise RateLimited("common.rate_limited", params={"retry_after": max(ttl, 1)})


async def hit(key: str, *, limit: int, window: timedelta) -> None:
    """Count one attempt; raise `common.rate_limited` once `limit` is exceeded within `window`."""
    full_key = _key(key)
    async with redis.pipeline(transaction=True) as pipe:
        pipe.incr(full_key)
        pipe.expire(full_key, int(window.total_seconds()), nx=True)  # atomic with INCR: never a key without TTL
        count, _ = await pipe.execute()
    if count > limit:
        ttl = await redis.ttl(full_key)
        raise RateLimited("common.rate_limited", params={"retry_after": max(ttl, 1)})
