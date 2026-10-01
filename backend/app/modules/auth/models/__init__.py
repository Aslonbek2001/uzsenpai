"""ORM models — imported here so Alembic autogenerate sees every table of the module."""

from app.modules.auth.models.identity import Identity
from app.modules.auth.models.session import Session

__all__ = ["Identity", "Session"]
