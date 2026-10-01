---
name: payments-billing
description: UzSenpai money architecture — catalog (products, prices per currency, entitlement keys), Money type, checkout, national (Click, Payme, Uzum — UZS) and international (USD/JPY/EUR) payment providers behind one PaymentProvider contract and registry, signed idempotent webhooks via a shared ledger, payment state machine, entitlement grants and quota, human-fulfilled orders, refunds, reconciliation. Use whenever touching catalog, billing, orders or experts modules, a payment provider, a paywall, checkout UI, prices or currencies, or any code path that grants access to a paid feature.
user-invocable: false
paths:
  - "backend/app/modules/catalog/**"
  - "backend/app/modules/billing/**"
  - "backend/app/modules/orders/**"
  - "backend/app/modules/experts/**"
  - "backend/app/shared/money.py"
  - "frontend/src/features/checkout-*/**"
---

# Payments & billing — national + international

Money code is boring on purpose: explicit states, idempotent steps, server-side amounts, integer minor units,
full audit trail, and every provider behind the same contract.

## Runnable reference (passes ruff, mypy --strict, 6 import-linter contracts and 25 billing tests on Postgres,
## including real-commit concurrency tests)

- `catalog`: [public.py](templates/app/modules/catalog/public.py), [testing.py](templates/app/modules/catalog/testing.py),
  [models/product.py](templates/app/modules/catalog/models/product.py) (Product + ProductPrice per currency),
  [domain/keys.py](templates/app/modules/catalog/domain/keys.py) (entitlement keys)
- `billing`: [public.py](templates/app/modules/billing/public.py) (`BillingFacade`, `require_entitlement`,
  `build_provider_registry`), [providers/base.py](templates/app/modules/billing/providers/base.py) (contract),
  [providers/registry.py](templates/app/modules/billing/providers/registry.py),
  [services/webhook_service.py](templates/app/modules/billing/services/webhook_service.py) (ledger),
  [services/checkout_service.py](templates/app/modules/billing/services/checkout_service.py),
  [services/entitlement_service.py](templates/app/modules/billing/services/entitlement_service.py),
  [routers/](templates/app/modules/billing/routers/__init__.py),
  tests: [flow](templates/app/modules/billing/tests/test_payments_flow.py),
  [concurrency & commit-before-ack](templates/app/modules/billing/tests/test_concurrency.py),
  [Payme JSON-RPC](templates/app/modules/billing/tests/test_payme_adapter.py)
- `catalog` public API for web and bot: [routers/products.py](templates/app/modules/catalog/routers/products.py)
  (`GET /api/v1/catalog/products?currency=` and `/products/{id}?currency=`, localized)
- Adapters: [fake/](templates/app/modules/billing/providers/fake/adapter.py) (complete, dev/tests only),
  [payme/](templates/app/modules/billing/providers/payme/adapter.py) (stateful JSON-RPC) and
  [click/](templates/app/modules/billing/providers/click/adapter.py) — both `ready=False` until verified (see below)
- `Money` lives in the `modular-monolith` templates: `app/shared/money.py`.

## Ownership

| Module | Owns | Public surface |
|---|---|---|
| `catalog` | products, **one price row per currency**, `LocalizedText` titles/bullets, what a product grants | `CatalogFacade.priced(product_id, currency)`, `Key`, `testing.create_product` |
| `billing` | payments, payment events, provider adapters, grants | `BillingFacade.has_access/consume`, `require_entitlement`, `build_provider_registry`, `PaymentSucceeded` |
| `orders` | human-fulfilled orders, status history, deliverables, SLA | created from `PaymentSucceeded` (fulfilment = human) |
| `experts` | expert profiles, availability, assignment | `assign`, `availability` |

## Currencies

- `Money(amount_minor: int, currency)` with ISO 4217 exponents (UZS 2, USD 2, JPY 0…). Never floats — parse
  provider decimals with `Decimal`. Adding different currencies raises.
- Catalog stores a price per currency. **No FX conversion anywhere.** UZS → national providers; USD/JPY/EUR →
  international provider. A product without a price in the requested currency → `catalog.price_not_available`.
- Frontend shows prices from the API with `fmt.money(amount_minor, currency, locale)`.

## Flow

```
UI → POST /api/v1/billing/checkout {product_id, currency, provider?}
  CheckoutService: CatalogFacade.priced() → registry.choose(currency, provider)
  → reuse a recent pending payment or create Payment(pending, amount, grants_snapshot, fulfilment)
  → adapter.create_checkout() → {payment_id, provider, redirect_url}
User pays at the provider
Provider → POST /api/v1/billing/webhooks/{provider}
  adapter: verify signature/auth, parse protocol → WebhookLedger.mark_paid/mark_failed
  ledger: lock payment row → paid with same txn? return same answer · paid with other txn? already_paid (409)
          → amount == price? → txn not used by another payment? → state machine → PaymentEvent
          → grants from the checkout SNAPSHOT → durable PaymentSucceeded (outbox) — one transaction,
          COMMITTED before the ack (SessionDep, scope="function"); commit failure → 5xx → provider retries
  adapter: returns the provider-specific ack (Payme JSON-RPC result, Click error=0 JSON, …)
Outbox → orders (human services), notifications (receipt in the user's locale)
```

## Provider contract (`providers/base.py`)

```python
class PaymentProvider(Protocol):
    name: str
    capabilities: ProviderCapabilities          # scope national|international, currencies, refunds, recurring
    async def create_checkout(self, req: CheckoutRequest) -> CheckoutSession: ...
    async def handle_webhook(self, request: Request, ledger: PaymentLedger) -> Response: ...
```

Adapters know the provider's protocol only: verify auth/signature FIRST, validate the payload (Pydantic), call the
ledger (`view`, `view_by_provider_txn`, `attach_provider_txn`, `save_provider_state`, `mark_paid`, `mark_failed`),
catch `AppError` and answer in the provider's own error format. Adapters may not import repositories or models
(import-linter). Business rules live in the ledger, so every provider gets identical guarantees.
Provider-specific data (e.g. Payme txn times/state) is stored in `payment.provider_state[<provider>]`.

### Adding a provider (national or international)

1. `/adr` — which provider, which currencies, fees, refund/recurring support, merchant entity requirements.
2. Read the provider's **current official merchant docs**; note version/date in the adapter docstring.
3. New package `providers/<name>/` — `adapter.py`, plus `signature.py` / `errors.py` / `schemas.py` as needed.
4. Register it in `build_provider_registry` (`billing/public.py`) and add its settings to `core/config.py`.
5. Tests: signature valid/invalid, every callback twice (idempotent), wrong amount, unknown payment, retry
   after success. Then the provider's sandbox end-to-end.
6. Set `capabilities.ready=True` only after step 5. Enable it via `PAYMENT_PROVIDERS_ENABLED`.
   Startup refuses: unknown names, missing credentials, `fake` outside local/test, `ready=False` outside local/test.

### Adapter status

| Provider | Scope | Status |
|---|---|---|
| `fake` | test/dev | complete (signed JSON webhooks) |
| `payme` | national, UZS (tiyin, JSON-RPC, Basic auth) | `ready=False`: Check/Create/Perform/Cancel/CheckTransaction implemented with stored state and tested; GetStatement missing; verify codes against docs + sandbox |
| `click` | national, UZS (prepare/complete, MD5 sign) | `ready=False`: prepare/complete with exact amounts, Click `error` handling, prepare-id check; verify fields/codes against docs + sandbox |
| `uzum` | national, UZS | not started — docs first |
| international | USD/JPY/EUR | provider undecided (docs/STACK.md) — ADR, then same contract |

## Payment state machine (`domain/state_machine.py`)

`pending → paid | failed | expired`, `failed | expired → paid` (late capture confirmation — the customer paid),
`paid → refunded`. Strict: repeats are handled by the ledger (same provider txn), never by the state machine.
A stale failure after success keeps `paid`. Every change writes a `billing_payment_events` row with the txn id.

## Entitlements

- Grant = (user_id, key, source_payment_id, remaining | null, expires_at | null, revoked_at, created_at, updated_at).
- `require_entitlement(Key.X)` as a router dependency, or `BillingFacade.has_access`.
- Quota features call `BillingFacade.consume` **after** success; decrement is an atomic `UPDATE … RETURNING`
  with a row lock and one retry (tested with 8 concurrent sessions: never over-uses quota).
- Grants come from the snapshot stored on the payment at checkout, so catalog edits can't lose a paid grant.
- Refund revokes that payment's grants. Subscriptions = grants with `expires_at`, renewed by the next payment.

## Orders (human services)

`created → paid → in_progress → delivered → completed`, plus `cancelled`, `refunded`; allowed-from check, actor,
timestamp, notification in the user's locale; SLA from the product; overdue orders in an admin list.

## Rules

- The client never sends an amount. Webhooks: no user auth, signature only; respond fast; heavy work via outbox.
- Money tables have `created_at`/`updated_at` and are append-only where possible.
- Nightly reconciliation job per provider compares statements with `billing_payments` and reports mismatches.
- In the Telegram bot, in-bot payment is an open decision (Telegram Stars rule) — the bot links to web checkout.
