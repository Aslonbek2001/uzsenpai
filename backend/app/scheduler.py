"""app/scheduler.py — Taskiq scheduler entry point: `taskiq scheduler app.scheduler:scheduler`.

Run exactly ONE scheduler process: it only enqueues periodic tasks (schedules declared with `schedule=[...]` on
the task), the worker executes them. Two schedulers would enqueue every periodic task twice.
"""

from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from app.worker import broker

scheduler = TaskiqScheduler(broker=broker, sources=[LabelScheduleSource(broker)])
