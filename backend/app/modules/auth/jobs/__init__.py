"""Background tasks of the auth module (imported by app/worker.py so Taskiq registers them)."""

from app.modules.auth.jobs.cleanup import purge_sessions

__all__ = ["purge_sessions"]
