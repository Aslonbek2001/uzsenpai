"""app/core/tasks.py — the Taskiq broker (ADR 0001). Modules define tasks in `modules/<name>/jobs/`.

Redis Streams broker: a task is acknowledged only after it finished, so a crashed worker's tasks are redelivered.
Tasks must therefore be idempotent. Tests use the in-memory broker (tasks run inline, no Redis needed).
"""

from taskiq import AsyncBroker, InMemoryBroker
from taskiq_redis import RedisStreamBroker

from app.core.config import settings


def _build_broker() -> AsyncBroker:
    if settings.env == "test":
        return InMemoryBroker()
    return RedisStreamBroker(url=settings.taskiq_broker_url)


broker = _build_broker()
