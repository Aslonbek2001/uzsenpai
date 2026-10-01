"""app/worker.py — Taskiq worker entry point: `taskiq worker app.worker:broker`.

Composition root for background work: import every module's `jobs` package here so its tasks are registered.
"""

from taskiq import TaskiqEvents, TaskiqState

from app.core.db import engine
from app.core.logging import configure_logging
from app.core.redis import redis
from app.core.tasks import broker

# One line per module with background tasks, e.g.:
# import app.modules.resume.jobs

__all__ = ["broker"]


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def _startup(_: TaskiqState) -> None:
    configure_logging()


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def _shutdown(_: TaskiqState) -> None:
    await redis.aclose()
    await engine.dispose()
