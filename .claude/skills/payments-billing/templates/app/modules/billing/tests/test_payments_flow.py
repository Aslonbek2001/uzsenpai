"""Checkout → provider webhook → entitlements, through the real app with the fake provider."""

import json
import uuid

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.outbox import OutboxMessage
from app.modules.billing.models import Grant, PaymentEvent
from app.modules.billing.providers.fake import FakeProvider
from app.modules.billing.public import BillingFacade

pytestmark = pytest.mark.asyncio


async def _webhook(client: AsyncClient, app: FastAPI, payload: dict[str, object]) -> int:
    provider: FakeProvider = app.state.payment_providers.get("fake")
    body = json.dumps(payload).encode()
    r = await client.post(
        "/api/v1/billing/webhooks/fake",
        content=body,
        headers={"x-fake-signature": provider.sign(body), "content-type": "application/json"},
    )
    return r.status_code


async def _checkout(client: AsyncClient, headers: dict[str, str], product: str, currency: str) -> str:
    r = await client.post(
        "/api/v1/billing/checkout",
        json={"product_id": product, "currency": currency, "provider": "fake"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return str(r.json()["payment_id"])


@pytest.mark.parametrize(("currency", "amount"), [("UZS", 9_900_000), ("JPY", 1200)])
async def test_paid_webhook_grants_quota_once(
    client: AsyncClient,
    app: FastAPI,
    auth_headers: dict[str, str],
    product: str,
    db_session: AsyncSession,
    currency: str,
    amount: int,
) -> None:
    payment_id = await _checkout(client, auth_headers, product, currency)
    payload = {"payment_id": payment_id, "txn_id": "T1", "amount_minor": amount, "currency": currency, "status": "paid"}
    assert await _webhook(client, app, payload) == 200
    assert await _webhook(client, app, payload) == 200  # provider retry — idempotent

    grants = (await db_session.scalars(select(Grant))).all()
    assert [(g.key, g.remaining) for g in grants] == [("interview.mock_session", 3)]
    assert await db_session.scalar(select(func.count()).select_from(PaymentEvent)) == 1
    assert (await db_session.scalars(select(OutboxMessage.name))).all() == ["PaymentSucceeded"]

    r = await client.get("/api/v1/billing/entitlements", headers=auth_headers)
    assert r.json()["keys"] == ["interview.mock_session"]


async def test_wrong_amount_is_rejected_and_nothing_granted(
    client: AsyncClient, app: FastAPI, auth_headers: dict[str, str], product: str, db_session: AsyncSession
) -> None:
    payment_id = await _checkout(client, auth_headers, product, "UZS")
    payload = {"payment_id": payment_id, "txn_id": "T2", "amount_minor": 1, "currency": "UZS", "status": "paid"}
    assert await _webhook(client, app, payload) == 409
    assert (await db_session.scalars(select(Grant))).all() == []


async def test_bad_signature_is_401(client: AsyncClient) -> None:
    r = await client.post("/api/v1/billing/webhooks/fake", content=b"{}", headers={"x-fake-signature": "nope"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "billing.invalid_signature"


async def test_currency_without_price_is_422(client: AsyncClient, auth_headers: dict[str, str], product: str) -> None:
    r = await client.post(
        "/api/v1/billing/checkout", json={"product_id": product, "currency": "USD"}, headers=auth_headers
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "catalog.price_not_available"


async def test_consume_after_success_until_empty(
    client: AsyncClient, app: FastAPI, auth_headers: dict[str, str], product: str, db_session: AsyncSession
) -> None:
    payment_id = await _checkout(client, auth_headers, product, "UZS")
    await _webhook(
        client,
        app,
        {"payment_id": payment_id, "txn_id": "T3", "amount_minor": 9_900_000, "currency": "UZS", "status": "paid"},
    )
    user_id = uuid.UUID(auth_headers["Authorization"].removeprefix("Bearer test-"))
    billing = BillingFacade(db_session)
    for _ in range(3):
        await billing.consume(user_id, "interview.mock_session")
    assert not await billing.has_access(user_id, "interview.mock_session")
    with pytest.raises(Exception, match=r"billing\.no_entitlement"):
        await billing.consume(user_id, "interview.mock_session")


async def test_default_provider_national_for_uzs_international_otherwise(
    client: AsyncClient, app: FastAPI, auth_headers: dict[str, str], product: str
) -> None:
    enabled = {p.name for c in ("UZS", "JPY") for p in app.state.payment_providers.for_currency(c)}
    r = await client.post(
        "/api/v1/billing/checkout", json={"product_id": product, "currency": "UZS"}, headers=auth_headers
    )
    expected_uzs = "payme" if "payme" in enabled else "fake"
    assert r.json()["provider"] == expected_uzs  # national first for UZS
    r = await client.post(
        "/api/v1/billing/checkout", json={"product_id": product, "currency": "JPY"}, headers=auth_headers
    )
    assert r.json()["provider"] == "fake"  # national providers don't take JPY → international


async def test_unknown_provider_is_rejected(client: AsyncClient, auth_headers: dict[str, str], product: str) -> None:
    r = await client.post(
        "/api/v1/billing/checkout",
        json={"product_id": product, "currency": "JPY", "provider": "payme"},
        headers=auth_headers,
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "billing.provider_not_available"
