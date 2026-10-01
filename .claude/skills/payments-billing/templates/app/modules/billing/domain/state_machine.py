"""The only allowed payment status transitions."""

from app.modules.billing.domain.enums import PaymentStatus
from app.modules.billing.domain.exceptions import InvalidTransition

ALLOWED: dict[PaymentStatus, frozenset[PaymentStatus]] = {
    PaymentStatus.PENDING: frozenset({PaymentStatus.PAID, PaymentStatus.FAILED, PaymentStatus.EXPIRED}),
    PaymentStatus.PAID: frozenset({PaymentStatus.REFUNDED}),
    # A provider can confirm capture after we marked the attempt failed/expired (late callback): the customer
    # paid, so accept it (the ledger still checks amount and txn) instead of losing the money.
    PaymentStatus.FAILED: frozenset({PaymentStatus.PAID}),
    PaymentStatus.EXPIRED: frozenset({PaymentStatus.PAID}),
    PaymentStatus.REFUNDED: frozenset(),
}


def transition(current: PaymentStatus, target: PaymentStatus) -> PaymentStatus:
    """Strict: callers handle idempotent repeats themselves (the ledger compares provider txn ids)."""
    if target not in ALLOWED[current]:
        raise InvalidTransition("billing.invalid_transition", params={"from": current.value, "to": target.value})
    return target
