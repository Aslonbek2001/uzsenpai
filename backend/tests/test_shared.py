"""Unit tests for app/shared value types — no DB."""

import pytest
from pydantic import ValidationError

from app.shared.i18n import Locale, LocalizedText
from app.shared.money import Money


def test_money_minor_units_per_currency() -> None:
    assert Money(15_000_000, "UZS").to_major_str() == "150000.00"
    assert Money(1500, "JPY").to_major_str() == "1500"


def test_money_rejects_floats_negatives_and_mixed_currencies() -> None:
    with pytest.raises(TypeError):
        Money(10.5, "USD")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match=">= 0"):
        Money(-1, "USD")
    with pytest.raises(ValueError, match="cannot add"):
        _ = Money(100, "USD") + Money(100, "JPY")


def test_localized_text_falls_back_to_uzbek() -> None:
    text = LocalizedText(uz="Salom", ja="こんにちは")
    assert text.resolve(Locale.JA) == ("こんにちは", Locale.JA)
    assert text.resolve(Locale.RU) == ("Salom", Locale.UZ)


def test_localized_text_requires_uzbek() -> None:
    with pytest.raises(ValidationError):
        LocalizedText(uz="  ")
