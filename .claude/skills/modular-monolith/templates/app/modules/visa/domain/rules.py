"""Domain rules — plain functions, no I/O, trivially unit-testable."""

from datetime import date

from app.modules.visa.domain.enums import Urgency
from app.modules.visa.domain.exceptions import ExpiryInPast

REMINDER_DAYS = (90, 60, 30)


def urgency_for(days_left: int) -> Urgency:
    if days_left < 0:
        return Urgency.EXPIRED
    if days_left < 30:
        return Urgency.URGENT
    if days_left < 90:
        return Urgency.SOON
    return Urgency.OK


def ensure_future(expires_on: date, today: date) -> None:
    if expires_on < today:
        raise ExpiryInPast("visa.expiry_in_past", params={"expires_on": expires_on.isoformat()})
