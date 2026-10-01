"""API contract for /visa/status (feeds OpenAPI → frontend types)."""

from datetime import date

from pydantic import BaseModel, Field

from app.modules.visa.domain.enums import ResidenceStatus, Urgency


class VisaStatusIn(BaseModel):
    residence_status: ResidenceStatus
    expires_on: date


class VisaStatusOut(BaseModel):
    residence_status: ResidenceStatus
    expires_on: date
    days_left: int = Field(description="Days until expiry; negative when expired")
    urgency: Urgency
