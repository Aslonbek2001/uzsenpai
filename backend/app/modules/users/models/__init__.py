"""ORM models — imported here so Alembic autogenerate sees every table of the module."""

from app.modules.users.models.user import User

__all__ = ["User"]
