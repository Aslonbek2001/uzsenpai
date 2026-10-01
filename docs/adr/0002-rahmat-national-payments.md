# 0002. Rahmat for national (UZS) payments

- Status: accepted
- Date: 2026-10-02

## Context
Paid services must be payable in UZS by users in Uzbekistan. The initial assumption was three separate
adapters (Click, Payme, Uzum). The owner already has access to Rahmat (rhmt.uz), a payment aggregator.
Constraints: solo developer, every provider behind the same `PaymentProvider` contract, fiscal receipts
are mandatory in Uzbekistan.

## Options
1. **Click + Payme + Uzum, separately** — direct contracts, reference adapters already exist for Payme/Click.
   Cons: three integrations, three contracts, three reconciliations; fiscalization handled by us.
2. **Rahmat** — one integration covers Humo, Uzcard, Visa/Mastercard and Click/Payme/Uzum and others;
   automatic fiscal receipts; split payments (useful for expert payouts later). Cons: API docs are not public
   (given after the merchant contract); one more intermediary in the money flow.

## Decision
Rahmat is the only national provider. One adapter, one contract and built-in fiscalization outweigh the
extra intermediary for a solo developer. If Rahmat also accepts foreign-issued cards or non-UZS currencies,
it may cover international payments too — see ADR 0003.

## Consequences
- New adapter `billing/providers/rahmat/`, built only after the merchant API docs and sandbox are available;
  until then development uses the `fake` provider. Preparation checklist: `docs/payments/rahmat.md`.
- `payme` / `click` templates in the `payments-billing` skill stay as reference adapters only.
- Products may need fiscal codes (MXIK/IKPU, package code) in `catalog` — confirm with Rahmat before the
  catalog schema is finalised.
- Revisit if Rahmat's API cannot meet the ledger guarantees (signed callbacks, idempotency, status lookup).
