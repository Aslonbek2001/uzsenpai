"""API contract for /users/me (feeds OpenAPI → frontend types)."""

import uuid
import zoneinfo
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.modules.users.domain.enums import JlptLevel, UserGoal, UserRole
from app.modules.users.domain.rules import DISPLAY_NAME_MAX
from app.shared.i18n import Locale

DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=DISPLAY_NAME_MAX)]
CountryCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]


class MeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    display_name: str
    locale: Locale
    role: UserRole
    residence_country: str | None
    timezone: str
    jlpt_level: JlptLevel | None
    goal: UserGoal | None
    onboarding_completed_at: datetime | None
    created_at: datetime


class MeUpdateIn(BaseModel):
    """Partial update: only the fields sent are changed. `null` clears an optional onboarding answer."""

    model_config = ConfigDict(extra="forbid")

    display_name: DisplayName | None = None
    locale: Locale | None = None
    residence_country: CountryCode | None = None
    timezone: str | None = Field(default=None, examples=["Asia/Tokyo"])
    jlpt_level: JlptLevel | None = None
    goal: UserGoal | None = None
    onboarding_completed: bool | None = Field(default=None, description="true marks onboarding as finished")

    @field_validator("timezone")
    @classmethod
    def _known_timezone(cls, value: str | None) -> str | None:
        if value is not None and value not in zoneinfo.available_timezones():
            raise ValueError("unknown IANA timezone")
        return value
