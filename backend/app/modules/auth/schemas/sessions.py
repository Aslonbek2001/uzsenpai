"""API contract for the "Devices" list."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class SessionOut(BaseModel):
    family_id: uuid.UUID  # stable id of the device / login; use it to sign that device out
    user_agent: str | None
    ip: str | None
    last_active_at: datetime
    expires_at: datetime
    current: bool  # the device making this request
