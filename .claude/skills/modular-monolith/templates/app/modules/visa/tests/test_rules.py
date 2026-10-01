"""Unit tests for pure domain rules — no DB, no HTTP."""

from datetime import date

import pytest

from app.modules.visa.domain.enums import Urgency
from app.modules.visa.domain.exceptions import ExpiryInPast
from app.modules.visa.domain.rules import ensure_future, urgency_for


@pytest.mark.parametrize(
    ("days", "expected"),
    [
        (-1, Urgency.EXPIRED),
        (0, Urgency.URGENT),
        (29, Urgency.URGENT),
        (30, Urgency.SOON),
        (89, Urgency.SOON),
        (90, Urgency.OK),
    ],
)
def test_urgency_boundaries(days: int, expected: Urgency) -> None:
    assert urgency_for(days) == expected


def test_past_expiry_is_rejected_with_code() -> None:
    with pytest.raises(ExpiryInPast) as exc:
        ensure_future(date(2026, 1, 1), today=date(2026, 10, 1))
    assert exc.value.code == "visa.expiry_in_past"
