import pytest

from app.modules.billing.domain.enums import PaymentStatus as S
from app.modules.billing.domain.exceptions import InvalidTransition
from app.modules.billing.domain.state_machine import transition
from app.modules.billing.providers.click.signature import expected_sign, is_valid
from app.shared.money import Money


def test_transitions() -> None:
    assert transition(S.PENDING, S.PAID) == S.PAID
    assert transition(S.FAILED, S.PAID) == S.PAID  # late capture confirmation is accepted
    with pytest.raises(InvalidTransition):
        transition(S.PAID, S.PAID)  # strict: the ledger handles retries by comparing provider txn ids
    with pytest.raises(InvalidTransition):
        transition(S.REFUNDED, S.PAID)


def test_money_rules() -> None:
    assert Money(15_000_000, "UZS").to_major_str() == "150000.00"
    assert Money(1500, "JPY").to_major_str() == "1500"
    with pytest.raises(ValueError):
        Money(1, "UZS") + Money(1, "USD")
    with pytest.raises(TypeError):
        Money(1.5, "USD")  # type: ignore[arg-type]


def test_click_signature_roundtrip() -> None:
    fields = dict(
        click_trans_id="1",
        service_id="2",
        secret_key="s",
        merchant_trans_id="p",
        amount="1000.00",
        action="0",
        sign_time="2026-10-01 10:00:00",
    )
    assert is_valid(expected_sign(**fields), **fields)
    assert not is_valid("bad", **fields)
