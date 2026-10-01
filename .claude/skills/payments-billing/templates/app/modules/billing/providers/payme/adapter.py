"""Payme Merchant API (JSON-RPC 2.0, amounts in tiyin, Basic auth "Paycom:<key>").

Transaction state lives in payment.provider_state["payme"] = {id, create_time, perform_time, cancel_time,
state (1 created, 2 performed, -1 cancelled), reason, amount}. Payme's txn id is attached to the payment at
CreateTransaction, so PerformTransaction/Cancel/Check find it by that id.

STATUS: ready=False — GetStatement is not implemented and the protocol must be verified against the official
docs + sandbox before production. Record the docs version/date here when you do.
"""

import base64
import hmac
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import quote

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.modules.billing.domain.enums import PaymentStatus, ProviderScope
from app.modules.billing.providers.base import (
    CheckoutRequest,
    CheckoutSession,
    PaymentLedger,
    PaymentView,
    ProviderCapabilities,
)
from app.modules.billing.providers.payme import errors as E
from app.modules.billing.providers.payme.schemas import CancelParams, CheckPerformParams, CreateParams, TxnParams
from app.shared.errors import AppError
from app.shared.money import Money

Result = dict[str, Any]


def _now_ms() -> int:
    return int(time.time() * 1000)


class PaymeProvider:
    name = "payme"
    capabilities = ProviderCapabilities(
        scope=ProviderScope.NATIONAL, currencies=frozenset({"UZS"}), refunds=True, ready=False
    )

    def __init__(self, merchant_id: str, key: str, checkout_url: str) -> None:
        self._merchant_id = merchant_id
        self._key = key
        self._checkout_url = checkout_url.rstrip("/")

    async def create_checkout(self, req: CheckoutRequest) -> CheckoutSession:
        params = f"m={self._merchant_id};ac.payment_id={req.payment_id};a={req.amount.amount_minor};l={req.locale}"
        token = base64.b64encode(params.encode()).decode()
        return CheckoutSession(redirect_url=f"{self._checkout_url}/{quote(token)}")

    def _authorized(self, request: Request) -> bool:
        if not self._key:
            return False
        expected = "Basic " + base64.b64encode(f"Paycom:{self._key}".encode()).decode()
        return hmac.compare_digest(request.headers.get("authorization", ""), expected)

    async def handle_webhook(self, request: Request, ledger: PaymentLedger) -> Response:
        raw = await request.body()
        try:
            body: dict[str, Any] = json.loads(raw)
        except ValueError:
            return JSONResponse(E.rpc_error(None, E.PARSE_ERROR, "Parse error"))
        rid = body.get("id") if isinstance(body, dict) else None
        if not self._authorized(request):  # auth before touching params
            return JSONResponse(E.rpc_error(rid, E.AUTH_FAILED, "Unauthorized"))
        methods: dict[str, Callable[[Any, dict[str, Any], PaymentLedger], Awaitable[Result]]] = {
            "CheckPerformTransaction": self._check_perform,
            "CreateTransaction": self._create,
            "PerformTransaction": self._perform,
            "CancelTransaction": self._cancel,
            "CheckTransaction": self._check,
        }
        handler = methods.get(str(body.get("method")))
        if handler is None:
            return JSONResponse(E.rpc_error(rid, E.METHOD_NOT_FOUND, "Method not supported"))
        try:
            return JSONResponse(await handler(rid, body.get("params") or {}, ledger))
        except ValidationError:
            return JSONResponse(E.rpc_error(rid, E.INVALID_REQUEST, "Invalid params"))
        except AppError as e:  # any ledger refusal → protocol error, never a 4xx/5xx to Payme
            return JSONResponse(E.rpc_error(rid, E.CANNOT_PERFORM, e.code))

    @staticmethod
    def _state(view: PaymentView) -> dict[str, Any]:
        return dict(view.provider_state.get("payme") or {})

    async def _check_perform(self, rid: Any, params: dict[str, Any], ledger: PaymentLedger) -> Result:
        p = CheckPerformParams.model_validate(params)
        view = await ledger.view(p.account.payment_id)
        if view is None or view.status != PaymentStatus.PENDING:
            return E.rpc_error(rid, E.ORDER_NOT_FOUND, "Payment not found")
        if view.amount != Money(p.amount, "UZS"):
            return E.rpc_error(rid, E.WRONG_AMOUNT, "Wrong amount")
        return {"id": rid, "result": {"allow": True}}

    async def _create(self, rid: Any, params: dict[str, Any], ledger: PaymentLedger) -> Result:
        p = CreateParams.model_validate(params)
        view = await ledger.view(p.account.payment_id)
        if view is None:
            return E.rpc_error(rid, E.ORDER_NOT_FOUND, "Payment not found")
        st = self._state(view)
        if st:  # a Payme transaction already exists for this payment
            if st["id"] == p.id:  # retry → same answer
                return {
                    "id": rid,
                    "result": {"create_time": st["create_time"], "transaction": str(view.id), "state": st["state"]},
                }
            return E.rpc_error(rid, E.ORDER_BUSY, "Another transaction is in progress")
        check = await self._check_perform(rid, params, ledger)
        if "error" in check:
            return check
        await ledger.attach_provider_txn(view.id, p.id)
        await ledger.save_provider_state(
            view.id,
            {
                "payme": {
                    "id": p.id,
                    "create_time": p.time,
                    "perform_time": 0,
                    "cancel_time": 0,
                    "state": 1,
                    "reason": None,
                    "amount": p.amount,
                }
            },
        )
        return {"id": rid, "result": {"create_time": p.time, "transaction": str(view.id), "state": 1}}

    async def _perform(self, rid: Any, params: dict[str, Any], ledger: PaymentLedger) -> Result:
        p = TxnParams.model_validate(params)
        view = await ledger.view_by_provider_txn(p.id)
        st = self._state(view) if view else {}
        if view is None or st.get("id") != p.id:  # only a transaction we created can be performed
            return E.rpc_error(rid, E.TRANSACTION_NOT_FOUND, "Transaction not found")
        if st["state"] == 2:
            return {"id": rid, "result": {"transaction": str(view.id), "perform_time": st["perform_time"], "state": 2}}
        if st["state"] != 1:
            return E.rpc_error(rid, E.CANNOT_PERFORM, "Cannot perform")
        # amount was checked against our price at Create and stored; the ledger checks it again
        await ledger.mark_paid(view.id, provider_txn_id=p.id, amount=Money(int(st["amount"]), "UZS"))
        st.update(state=2, perform_time=_now_ms())
        await ledger.save_provider_state(view.id, {"payme": st})
        return {"id": rid, "result": {"transaction": str(view.id), "perform_time": st["perform_time"], "state": 2}}

    async def _cancel(self, rid: Any, params: dict[str, Any], ledger: PaymentLedger) -> Result:
        p = CancelParams.model_validate(params)
        view = await ledger.view_by_provider_txn(p.id)
        st = self._state(view) if view else {}
        if view is None or st.get("id") != p.id:
            return E.rpc_error(rid, E.TRANSACTION_NOT_FOUND, "Transaction not found")
        if st["state"] == 2:  # performed → refunds go through the manual refund flow
            return E.rpc_error(rid, E.CANNOT_CANCEL, "Order completed; refund manually")
        if st["state"] == 1:
            await ledger.mark_failed(view.id, provider_txn_id=p.id)
            st.update(state=-1, cancel_time=_now_ms(), reason=p.reason)
            await ledger.save_provider_state(view.id, {"payme": st})
        return {
            "id": rid,
            "result": {"transaction": str(view.id), "cancel_time": st["cancel_time"], "state": st["state"]},
        }

    async def _check(self, rid: Any, params: dict[str, Any], ledger: PaymentLedger) -> Result:
        p = TxnParams.model_validate(params)
        view = await ledger.view_by_provider_txn(p.id)
        st = self._state(view) if view else {}
        if view is None or st.get("id") != p.id:
            return E.rpc_error(rid, E.TRANSACTION_NOT_FOUND, "Transaction not found")
        return {
            "id": rid,
            "result": {k: st[k] for k in ("create_time", "perform_time", "cancel_time", "state", "reason")}
            | {"transaction": str(view.id)},
        }
