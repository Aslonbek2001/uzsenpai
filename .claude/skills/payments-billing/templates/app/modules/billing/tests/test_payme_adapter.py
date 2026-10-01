"""Payme JSON-RPC flow against our ledger (runs when payme is enabled, e.g. PAYMENT_PROVIDERS_ENABLED + PAYME_*)."""

import base64
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio
PRICE = 9_900_000


@pytest.fixture
def payme(app: FastAPI) -> Any:
    if "payme" not in {p.name for p in app.state.payment_providers.for_currency("UZS")}:
        pytest.skip("payme not enabled")
    return app.state.payment_providers.get("payme")


async def _rpc(client: AsyncClient, key: str, method: str, params: dict[str, Any]) -> dict[str, Any]:
    auth = {"Authorization": "Basic " + base64.b64encode(f"Paycom:{key}".encode()).decode()}
    r = await client.post(
        "/api/v1/billing/webhooks/payme", json={"id": 1, "method": method, "params": params}, headers=auth
    )
    assert r.status_code == 200  # Payme always gets HTTP 200 with a JSON-RPC result or error
    return dict(r.json())


async def _checkout(client: AsyncClient, headers: dict[str, str], product: str) -> str:
    r = await client.post(
        "/api/v1/billing/checkout",
        json={"product_id": product, "currency": "UZS", "provider": "payme"},
        headers=headers,
    )
    return str(r.json()["payment_id"])


async def test_full_flow(client: AsyncClient, payme: Any, auth_headers: dict[str, str], product: str) -> None:
    key = payme._key
    pid = await _checkout(client, auth_headers, product)
    account = {"payment_id": pid}

    assert (await _rpc(client, "wrong", "CheckPerformTransaction", {"amount": PRICE, "account": account}))["error"][
        "code"
    ] == -32504
    assert (await _rpc(client, key, "CheckPerformTransaction", {"amount": 1, "account": account}))["error"][
        "code"
    ] == -31001
    assert (await _rpc(client, key, "CheckPerformTransaction", {"amount": PRICE, "account": account}))["result"] == {
        "allow": True
    }

    # Perform without our Create → not found (no free grants via forged ids)
    assert (await _rpc(client, key, "PerformTransaction", {"id": "forged"}))["error"]["code"] == -31003

    created = await _rpc(client, key, "CreateTransaction", {"id": "P1", "time": 1, "amount": PRICE, "account": account})
    assert created["result"]["state"] == 1
    again = await _rpc(client, key, "CreateTransaction", {"id": "P1", "time": 1, "amount": PRICE, "account": account})
    assert again["result"] == created["result"]  # idempotent
    busy = await _rpc(client, key, "CreateTransaction", {"id": "P2", "time": 2, "amount": PRICE, "account": account})
    assert busy["error"]["code"] == -31051

    performed = await _rpc(client, key, "PerformTransaction", {"id": "P1"})
    assert performed["result"]["state"] == 2
    assert (await _rpc(client, key, "PerformTransaction", {"id": "P1"}))["result"] == performed["result"]
    assert (await _rpc(client, key, "CheckTransaction", {"id": "P1"}))["result"]["state"] == 2
    assert (await _rpc(client, key, "CancelTransaction", {"id": "P1", "reason": 5}))["error"]["code"] == -31007

    r = await client.get("/api/v1/billing/entitlements", headers=auth_headers)
    assert r.json()["keys"] == ["interview.mock_session"]


async def test_cancel_before_perform(
    client: AsyncClient, payme: Any, auth_headers: dict[str, str], product: str
) -> None:
    key = payme._key
    pid = await _checkout(client, auth_headers, product)
    await _rpc(
        client, key, "CreateTransaction", {"id": "C1", "time": 1, "amount": PRICE, "account": {"payment_id": pid}}
    )
    cancelled = await _rpc(client, key, "CancelTransaction", {"id": "C1", "reason": 3})
    assert cancelled["result"]["state"] == -1
    assert (await _rpc(client, key, "PerformTransaction", {"id": "C1"}))["error"]["code"] == -31008


async def test_garbage_body_and_bad_params(client: AsyncClient, payme: Any) -> None:
    auth = {"Authorization": "Basic " + base64.b64encode(f"Paycom:{payme._key}".encode()).decode()}
    r = await client.post("/api/v1/billing/webhooks/payme", content=b"{not json", headers=auth)
    assert r.json()["error"]["code"] == -32700
    assert (await _rpc(client, payme._key, "CheckPerformTransaction", {"amount": "x"}))["error"]["code"] == -32600
