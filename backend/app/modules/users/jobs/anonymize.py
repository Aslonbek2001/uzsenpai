"""Daily: anonymize accounts whose 30-day deletion grace period has ended."""

from app.core.db import unit_of_work
from app.core.tasks import broker
from app.modules.users.services import DeletionService


@broker.task(task_name="users.anonymize_deleted", schedule=[{"cron": "40 2 * * *"}])
async def anonymize_deleted_users() -> None:
    while True:  # one transaction per batch, so a failure keeps earlier batches
        async with unit_of_work() as session:
            if await DeletionService(session).anonymize_due() == 0:
                return
