"""Background tasks of the users module (imported by app/worker.py so Taskiq registers them)."""

from app.modules.users.jobs.anonymize import anonymize_deleted_users

__all__ = ["anonymize_deleted_users"]
