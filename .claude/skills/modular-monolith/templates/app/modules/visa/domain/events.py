"""Events this module publishes."""

import uuid
from dataclasses import dataclass
from datetime import date

from app.core.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class VisaStatusSaved(DomainEvent):
    user_id: uuid.UUID
    expires_on: date
