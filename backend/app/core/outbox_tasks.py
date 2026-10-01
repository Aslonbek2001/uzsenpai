"""app/core/outbox_tasks.py — Taskiq tasks that drive the outbox.

- `kick`  — called right after commit: one task per new row, so events are handled within ~a second.
- sweep   — every 30 s: rows whose kick was lost, and retries that became due.
- purge   — daily: delete rows delivered more than 30 days ago.
Schedules run only in the single `scheduler` process (`taskiq scheduler app.scheduler:scheduler`).
"""

import uuid
from collections.abc import Sequence

from app.core.outbox_processor import process_message, purge_processed, sweep
from app.core.tasks import broker


@broker.task(task_name="core.outbox.process")
async def process_outbox_message(message_id: str) -> None:
    await process_message(uuid.UUID(message_id))


@broker.task(task_name="core.outbox.sweep", schedule=[{"interval": 30}])
async def sweep_outbox() -> None:
    await sweep()


@broker.task(task_name="core.outbox.purge", schedule=[{"cron": "17 3 * * *"}])
async def purge_outbox() -> None:
    await purge_processed()


async def kick(message_ids: Sequence[uuid.UUID]) -> None:
    for message_id in message_ids:
        await process_outbox_message.kiq(str(message_id))
