"""app/core/health.py — liveness and readiness probes for compose, Caddy and uptime checks."""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.db import engine
from app.core.redis import redis

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("")
async def live() -> dict[str, str]:
    """The process is up. Never touches dependencies, so a DB outage doesn't restart the API."""
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> JSONResponse:
    """Postgres and Redis are reachable — 503 otherwise, so traffic isn't routed to a broken instance."""
    checks: dict[str, str] = {}
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:
        log.exception("readiness: postgres unreachable")
        checks["postgres"] = "fail"
    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:
        log.exception("readiness: redis unreachable")
        checks["redis"] = "fail"
    healthy = all(v == "ok" for v in checks.values())
    return JSONResponse(status_code=200 if healthy else 503, content={"status": "ok" if healthy else "fail", **checks})
