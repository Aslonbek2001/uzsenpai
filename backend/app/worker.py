"""app/worker.py — Taskiq worker entry point: `taskiq worker app.worker:broker`.

Composition root for background work: import every module's `jobs` package here so its tasks are registered.
"""

from taskiq import TaskiqEvents, TaskiqState

import app.core.outbox_tasks  # noqa: F401  (registers outbox process/sweep/purge tasks)
from app.core.db import engine
from app.core.logging import configure_logging
from app.core.redis import redis
from app.core.tasks import broker
from app.wiring import wire_events

# One line per module with background tasks, e.g.:
# import app.modules.resume.jobs

__all__ = ["broker"]

wire_events()  # the worker runs durable handlers, so it needs the same subscriptions as the API


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def _startup(_: TaskiqState) -> None:
    configure_logging()


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def _shutdown(_: TaskiqState) -> None:
    await redis.aclose()
    await engine.dispose()
