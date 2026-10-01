# Rahmat integration — preparation

Status: **waiting for merchant contract and API docs.** Development uses the `fake` provider until then.
Decision: [ADR 0002](../adr/0002-rahmat-national-payments.md). Contact: phone 1865, Telegram @rhmt_support_bot,
site https://rhmt.uz/acquiring/online/

## 1. Questions to ask Rahmat (before signing)

Integration
- [ ] API documentation and a **sandbox / test mode** with test cards — link and access.
- [ ] Payment flow: hosted payment page (redirect) or API + widget? Can we pass our own `order_id` and get it back?
- [ ] Callbacks / webhooks: format, **signature algorithm**, retry policy, source IP list.
- [ ] Payment status lookup API (for reconciliation if a callback is lost).
- [ ] Refunds (full / partial) via API? Time limits?
- [ ] Payment link lifetime (expiry) and how a cancelled / expired payment is reported.
- [ ] Return URLs after payment (success / fail) — can they differ per locale (uz, ru, en, ja)?
- [ ] Payment page languages — is there uz / ru / en? Can we pass the language?

International (decides ADR 0003: yes → Rahmat covers everything, no → add Octo)
- [ ] Are **foreign-issued** Visa / Mastercard (e.g. cards from Japan) accepted?
- [ ] Can we charge in **USD or JPY**, or only UZS? If only UZS — who converts, and what does the payer see?

Money and legal
- [ ] Fees per method (cards, Click, Payme, Uzum…), settlement period, minimum / maximum amount.
- [ ] Merchant requirements: legal entity (MChJ / YaTT), documents, bank account.
- [ ] Fiscalization: which **MXIK (IKPU) code and package code** fit our services (online consultations,
      document preparation, education)? Who sends the receipt — Rahmat automatically, or we pass data?
- [ ] Split payments: conditions — could part of a payment go directly to an expert (行政書士)?
- [ ] Recurring payments / saved cards (for future subscriptions)?

## 2. What the owner prepares

- [ ] Legal entity documents and bank details required by Rahmat.
- [ ] List of paid services with UZS prices (goes into `catalog`, never into code).
- [ ] Refund policy and public offer (ommaviy oferta) text in uz / ru / en / ja — shown before payment.
- [ ] Support contact shown on receipts.

## 3. What we give Rahmat (filled in when the backend is deployed)

| Item | Value |
|---|---|
| Callback (webhook) URL | `https://<domain>/api/v1/billing/webhooks/rahmat` |
| Success / fail return URLs | `https://<domain>/<locale>/checkout/result?payment=<id>` |
| Server IPs (if they whitelist) | after hosting is chosen |

## 4. What our side already has (architecture)

- `PaymentProvider` contract + registry, shared `WebhookLedger` (idempotency, amount check, state machine,
  grants, durable `PaymentSucceeded`), `fake` provider for dev — see the `payments-billing` skill.
- Startup refuses a provider without credentials or with `ready=False` outside local/test.

## 5. Settings expected (names final once docs arrive)

`RAHMAT_MERCHANT_ID`, `RAHMAT_SECRET_KEY`, `RAHMAT_API_URL` — in `backend/.env` only, listed in
`backend/.env.example` without values. Enable with `PAYMENT_PROVIDERS_ENABLED=rahmat`.

## 6. Done when

Adapter passes: signature valid / invalid, every callback twice (idempotent), wrong amount, unknown payment,
retry after success, status lookup — then sandbox end-to-end. Only then `capabilities.ready=True`.
