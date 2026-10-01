"""Click SHOP-API: two callbacks — prepare (action=0) and complete (action=1), form-encoded, MD5-signed.

STATUS: ready=False — verify fields, error codes and responses against the official docs + sandbox before
enabling it in production. Record the docs version/date here.
"""

import uuid
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from app.modules.billing.domain.enums import PaymentStatus, ProviderScope
from app.modules.billing.domain.exceptions import AlreadyPaid, AmountMismatch, PaymentNotFound
from app.modules.billing.providers.base import CheckoutRequest, CheckoutSession, PaymentLedger, ProviderCapabilities
from app.modules.billing.providers.click.signature import is_valid
from app.shared.errors import AppError
from app.shared.money import Money

OK, SIGN_FAILED, WRONG_AMOUNT, ACTION_NOT_FOUND, ALREADY_PAID, ORDER_NOT_FOUND, TXN_NOT_FOUND, CANCELLED = (
    0,
    -1,
    -2,
    -3,
    -4,
    -5,
    -6,
    -9,
)


class ClickCallback(BaseModel):
    click_trans_id: str
    service_id: str
    merchant_trans_id: str
    amount: str
    action: str
    error: int = 0
    sign_time: str
    sign_string: str
    merchant_prepare_id: str | None = None


def _to_money(amount: str) -> Money | None:
    """Exact decimal → tiyin; anything with sub-tiyin precision is rejected (no rounding of money)."""
    try:
        minor = Decimal(amount) * 100
    except InvalidOperation:
        return None
    if minor != minor.to_integral_value() or minor < 0:
        return None
    return Money(int(minor), "UZS")


class ClickProvider:
    name = "click"
    capabilities = ProviderCapabilities(scope=ProviderScope.NATIONAL, currencies=frozenset({"UZS"}), ready=False)

    def __init__(self, service_id: str, merchant_id: str, secret_key: str, checkout_url: str) -> None:
        self._service_id = service_id
        self._merchant_id = merchant_id
        self._secret = secret_key
        self._checkout_url = checkout_url

    async def create_checkout(self, req: CheckoutRequest) -> CheckoutSession:
        query = urlencode(
            {
                "service_id": self._service_id,
                "merchant_id": self._merchant_id,
                "amount": req.amount.to_major_str(),
                "transaction_param": str(req.payment_id),
                "return_url": req.return_url,
            }
        )
        return CheckoutSession(redirect_url=f"{self._checkout_url}?{query}")

    async def handle_webhook(self, request: Request, ledger: PaymentLedger) -> Response:
        form = {k: str(v) for k, v in (await request.form()).items()}
        try:
            cb = ClickCallback.model_validate(form)
        except ValidationError:
            return JSONResponse({"error": SIGN_FAILED, "error_note": "Bad request"})
        reply: dict[str, object] = {"click_trans_id": cb.click_trans_id, "merchant_trans_id": cb.merchant_trans_id}

        def answer(code: int, note: str, **extra: object) -> JSONResponse:
            return JSONResponse({**reply, **extra, "error": code, "error_note": note})

        if not self._secret or not is_valid(
            cb.sign_string,
            click_trans_id=cb.click_trans_id,
            service_id=cb.service_id,
            secret_key=self._secret,
            merchant_trans_id=cb.merchant_trans_id,
            amount=cb.amount,
            action=cb.action,
            sign_time=cb.sign_time,
            merchant_prepare_id=cb.merchant_prepare_id if cb.action == "1" else None,
        ):
            return answer(SIGN_FAILED, "SIGN CHECK FAILED")
        try:
            payment_id = uuid.UUID(cb.merchant_trans_id)
        except ValueError:
            return answer(ORDER_NOT_FOUND, "Order not found")
        view = await ledger.view(payment_id)
        if view is None:
            return answer(ORDER_NOT_FOUND, "Order not found")
        amount = _to_money(cb.amount)
        if amount is None or amount != view.amount:
            return answer(WRONG_AMOUNT, "Incorrect amount")

        try:
            if cb.action == "0":  # prepare
                if view.status == PaymentStatus.PAID:
                    return answer(ALREADY_PAID, "Already paid")
                return answer(OK, "Success", merchant_prepare_id=str(payment_id))
            if cb.action != "1":
                return answer(ACTION_NOT_FOUND, "Action not found")
            if cb.merchant_prepare_id != str(payment_id):  # complete must follow our own prepare
                return answer(TXN_NOT_FOUND, "Transaction does not exist")
            if cb.error != 0:  # Click reports the payment failed on its side → cancel, never grant
                await ledger.mark_failed(payment_id, provider_txn_id=cb.click_trans_id)
                return answer(CANCELLED, "Transaction cancelled")
            await ledger.mark_paid(payment_id, provider_txn_id=cb.click_trans_id, amount=amount)
            return answer(OK, "Success", merchant_confirm_id=str(payment_id))
        except AlreadyPaid:
            return answer(ALREADY_PAID, "Already paid")
        except AmountMismatch:
            return answer(WRONG_AMOUNT, "Incorrect amount")
        except PaymentNotFound:
            return answer(ORDER_NOT_FOUND, "Order not found")
        except AppError:
            return answer(CANCELLED, "Transaction cancelled")
