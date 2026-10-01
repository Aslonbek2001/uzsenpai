"""Local/dev/test provider: "redirects" to a fake page; webhook JSON {payment_id, txn_id, amount_minor, currency,
status}, HMAC-signed in a header so tests exercise the same verification path as real providers.
Allowed only when settings.is_local — build_provider_registry refuses it elsewhere."""

import hmac
from hashlib import sha256
from typing import Literal
from urllib.parse import urlencode

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from pydantic import UUID4, BaseModel, StrictInt, ValidationError

from app.modules.billing.domain.enums import ProviderScope
from app.modules.billing.providers.base import CheckoutRequest, CheckoutSession, PaymentLedger, ProviderCapabilities
from app.shared.errors import AppError
from app.shared.money import Money


class FakeWebhook(BaseModel):
    payment_id: UUID4
    txn_id: str
    amount_minor: StrictInt
    currency: str
    status: Literal["paid", "failed"]


class FakeProvider:
    name = "fake"
    capabilities = ProviderCapabilities(
        scope=ProviderScope.INTERNATIONAL, currencies=frozenset({"UZS", "USD", "JPY"}), refunds=True
    )

    def __init__(self, secret: str) -> None:
        self._secret = secret.encode()

    def sign(self, body: bytes) -> str:
        return hmac.new(self._secret, body, sha256).hexdigest()

    async def create_checkout(self, req: CheckoutRequest) -> CheckoutSession:
        query = urlencode({"payment_id": str(req.payment_id), "return": req.return_url})
        return CheckoutSession(redirect_url=f"https://pay.fake.local/checkout?{query}")

    async def handle_webhook(self, request: Request, ledger: PaymentLedger) -> Response:
        body = await request.body()
        if not hmac.compare_digest(self.sign(body), request.headers.get("x-fake-signature", "")):
            return JSONResponse({"error": {"code": "billing.invalid_signature", "params": {}}}, status_code=401)
        try:
            data = FakeWebhook.model_validate_json(body)
            if data.status == "paid":
                await ledger.mark_paid(
                    data.payment_id, provider_txn_id=data.txn_id, amount=Money(data.amount_minor, data.currency)
                )
            else:
                await ledger.mark_failed(data.payment_id, provider_txn_id=data.txn_id)
        except ValidationError:
            return JSONResponse({"error": {"code": "billing.invalid_payload", "params": {}}}, status_code=400)
        except ValueError:  # e.g. unsupported currency in Money
            return JSONResponse({"error": {"code": "billing.invalid_payload", "params": {}}}, status_code=400)
        except AppError as e:
            return JSONResponse({"error": {"code": e.code, "params": e.params}}, status_code=e.status)
        return JSONResponse({"ok": True})
