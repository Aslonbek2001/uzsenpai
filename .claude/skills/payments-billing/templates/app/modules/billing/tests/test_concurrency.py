"""Money-path guarantees under REAL commits and concurrency (no savepoint override): each test drives the real
get_session, so these also prove the COMMIT happens before the provider receives its ack."""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionFactory
from app.core.outbox import OutboxMessage
from app.modules.billing.models import Grant, Payment
from app.modules.billing.public import BillingFacade
from app.modules.catalog.testing import create_product, set_product_active

pytestmark = pytest.mark.asyncio
UID = uuid.UUID("00000000-0000-0000-0000-0000000000aa")
HEADERS = {"Authorization": f"Bearer test-{UID}"}
Real = tuple[FastAPI, AsyncClient]


@pytest.fixture
async def real(committing_app: FastAPI) -> AsyncIterator[Real]:
    async with SessionFactory() as s:
        await create_product(s, "race", prices={"UZS": 1000}, grants=[{"key": "k.q", "quantity": 1, "days": None}])
        await s.commit()
    transport = ASGITransport(app=committing_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://t", headers=HEADERS) as c:
        yield committing_app, c


async def _hook(real: Real, payload: dict[str, Any]) -> int:
    app, c = real
    body = json.dumps(payload).encode()
    sig = app.state.payment_providers.get("fake").sign(body)
    r = await c.post(
        "/api/v1/billing/webhooks/fake",
        content=body,
        headers={"x-fake-signature": sig, "content-type": "application/json"},
    )
    return r.status_code


async def _pay(real: Real) -> str:
    _, c = real
    r = await c.post("/api/v1/billing/checkout", json={"product_id": "race", "currency": "UZS", "provider": "fake"})
    assert r.status_code == 201, r.text
    return str(r.json()["payment_id"])


def _paid(pid: str, txn: str) -> dict[str, Any]:
    return {"payment_id": pid, "txn_id": txn, "amount_minor": 1000, "currency": "UZS", "status": "paid"}


async def _counts() -> tuple[int, int]:
    async with SessionFactory() as s:
        grants = await s.scalar(select(func.count()).select_from(Grant))
        events = await s.scalar(select(func.count()).select_from(OutboxMessage))
        return int(grants or 0), int(events or 0)


async def _status(pid: str) -> str | None:
    async with SessionFactory() as s:
        return await s.scalar(select(Payment.status).where(Payment.id == uuid.UUID(pid)))


async def test_concurrent_duplicates_of_same_txn_grant_once(real: Real) -> None:
    pid = await _pay(real)
    codes = await asyncio.gather(*[_hook(real, _paid(pid, "T")) for _ in range(5)])
    assert set(codes) == {200}
    assert await _counts() == (1, 1)


async def test_different_txn_on_paid_payment_is_refused(real: Real) -> None:
    pid = await _pay(real)
    assert await _hook(real, _paid(pid, "T1")) == 200
    assert await _hook(real, _paid(pid, "T2")) == 409  # billing.already_paid
    assert await _counts() == (1, 1)


async def test_concurrent_different_txns_grant_once(real: Real) -> None:
    pid = await _pay(real)
    codes = await asyncio.gather(*[_hook(real, _paid(pid, f"X{i}")) for i in range(4)])
    assert sorted(codes) == [200, 409, 409, 409]
    assert await _counts() == (1, 1)


async def test_txn_reused_on_another_payment_is_409_not_500(real: Real) -> None:
    p1 = await _pay(real)
    _, c = real
    r = await c.post("/api/v1/billing/checkout", json={"product_id": "race", "currency": "UZS", "provider": "fake"})
    assert r.json()["payment_id"] == p1  # open checkout reused instead of a new pending row
    async with SessionFactory() as s:  # force a second pending payment
        p2 = Payment(
            user_id=UID,
            product_id="race",
            amount_minor=1000,
            currency="UZS",
            provider="fake",
            provider_state={},
            grants_snapshot=[],
            fulfilment="ai",
            status="pending",
        )
        s.add(p2)
        await s.commit()
    assert await _hook(real, _paid(p1, "SAME")) == 200
    assert await _hook(real, _paid(str(p2.id), "SAME")) == 409  # billing.txn_already_used


async def test_late_success_after_failure_is_accepted(real: Real) -> None:
    pid = await _pay(real)
    assert await _hook(real, {**_paid(pid, "F"), "status": "failed"}) == 200
    assert await _hook(real, _paid(pid, "P")) == 200  # customer was charged → grant, don't lose the money
    assert await _status(pid) == "paid"
    assert await _hook(real, {**_paid(pid, "P"), "status": "failed"}) == 200  # stale failure keeps "paid"
    assert await _status(pid) == "paid"


async def test_catalog_change_after_checkout_still_grants(real: Real) -> None:
    pid = await _pay(real)
    async with SessionFactory() as s:
        await set_product_active(s, "race", active=False)
        await s.commit()
    assert await _hook(real, _paid(pid, "D")) == 200  # grants come from the checkout snapshot
    assert await _counts() == (1, 1)


async def test_commit_failure_is_never_acked(real: Real, monkeypatch: pytest.MonkeyPatch) -> None:
    pid = await _pay(real)

    async def failing_commit(self: AsyncSession) -> None:
        raise RuntimeError("commit failed")

    monkeypatch.setattr(AsyncSession, "commit", failing_commit)
    code = await _hook(real, _paid(pid, "A"))
    monkeypatch.undo()
    assert code >= 500  # provider will retry
    assert await _status(pid) == "pending"


@pytest.mark.parametrize(
    "payload",
    [
        {"payment_id": "not-a-uuid", "status": "paid"},
        {"payment_id": str(uuid.uuid4()), "txn_id": "x", "amount_minor": 1.0, "currency": "UZS", "status": "paid"},
        {"payment_id": str(uuid.uuid4()), "txn_id": "x", "amount_minor": 1, "currency": "XXX", "status": "paid"},
    ],
)
async def test_malformed_payloads_are_400(real: Real, payload: dict[str, Any]) -> None:
    assert await _hook(real, payload) == 400


async def test_concurrent_consume_never_overuses_quota(real: Real) -> None:
    async with SessionFactory() as s:
        for i in range(2):
            pid = uuid.uuid4()
            s.add(
                Payment(
                    id=pid,
                    user_id=UID,
                    product_id="race",
                    amount_minor=1,
                    currency="UZS",
                    provider="fake",
                    provider_state={},
                    grants_snapshot=[],
                    fulfilment="ai",
                    status="paid",
                    provider_txn_id=f"c{i}",
                )
            )
            await s.flush()
            s.add(Grant(user_id=UID, key="k.c", source_payment_id=pid, remaining=2, expires_at=None))
        await s.commit()

    async def one() -> str:
        async with SessionFactory() as s:
            try:
                await BillingFacade(s).consume(UID, "k.c")
                await asyncio.sleep(0.05)
                await s.commit()
                return "ok"
            except Exception as e:
                await s.rollback()
                return type(e).__name__

    results = await asyncio.gather(*[one() for _ in range(8)])
    async with SessionFactory() as s:
        remaining = (await s.scalars(select(Grant.remaining).where(Grant.key == "k.c"))).all()
    assert results.count("ok") == 4
    assert sorted(r or 0 for r in remaining) == [0, 0]
