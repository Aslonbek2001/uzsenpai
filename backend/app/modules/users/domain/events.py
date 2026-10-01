"""Events of the users module — published durably; other modules react through their handlers/."""

import uuid
from dataclasses import dataclass

from app.core.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class UserDeletionRequested(DomainEvent):
    """Sign the user out everywhere now; data stays until anonymization (restorable for 30 days)."""

    user_id: uuid.UUID


@dataclass(frozen=True, kw_only=True)
class UserDeleted(DomainEvent):
    """Grace period over: personal data must be removed by every module that holds some."""

    user_id: uuid.UUID
