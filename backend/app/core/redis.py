"""app/core/redis.py — one shared async Redis client for cache and rate limits (DB index from REDIS_URL)."""

from redis.asyncio import Redis

from app.core.config import settings

redis = Redis.from_url(settings.redis_url, decode_responses=True)
