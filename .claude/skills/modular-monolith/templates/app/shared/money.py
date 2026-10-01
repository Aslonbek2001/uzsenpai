"""app/shared/money.py — money is an integer amount of MINOR units + an ISO 4217 currency. Never floats.

National (UZS) and international (USD, JPY, EUR…) payments share this type. No implicit conversion:
the catalog stores a price per currency; adding two different currencies is an error.
"""

from __future__ import annotations

from dataclasses import dataclass

# ISO 4217 minor-unit exponents for currencies we accept (add here before selling in a new currency)
MINOR_UNITS: dict[str, int] = {"UZS": 2, "USD": 2, "EUR": 2, "JPY": 0, "RUB": 2, "KZT": 2}


@dataclass(frozen=True, slots=True)
class Money:
    amount_minor: int
    currency: str

    def __post_init__(self) -> None:
        if self.currency not in MINOR_UNITS:
            raise ValueError(f"unsupported currency {self.currency}")
        if not isinstance(self.amount_minor, int) or isinstance(self.amount_minor, bool):
            raise TypeError("amount_minor must be an int (minor units)")
        if self.amount_minor < 0:
            raise ValueError("amount_minor must be >= 0")

    @property
    def exponent(self) -> int:
        return MINOR_UNITS[self.currency]

    def __add__(self, other: Money) -> Money:
        if other.currency != self.currency:
            raise ValueError(f"cannot add {self.currency} and {other.currency}")
        return Money(self.amount_minor + other.amount_minor, self.currency)

    def to_major_str(self) -> str:
        """'150000.00' for UZS, '1500' for JPY — for provider APIs that want decimal strings."""
        if self.exponent == 0:
            return str(self.amount_minor)
        major, minor = divmod(self.amount_minor, 10**self.exponent)
        return f"{major}.{minor:0{self.exponent}d}"
