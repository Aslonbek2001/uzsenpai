# 0003. International payments: Rahmat first, Octo as fallback

- Status: accepted
- Date: 2026-10-02

## Context
Many users live in Japan and pay with Japanese-issued Visa/Mastercard. The merchant is an Uzbekistan entity.
Part of the catalogue is human services (expert consultations, resume review), not only digital products.
Constraint: one `PaymentProvider` contract, minimal number of integrations for a solo developer.

## Options
1. **Rahmat** (already chosen for UZS, ADR 0002) — accepts Visa/Mastercard, but foreign-issued cards and
   non-UZS currencies are not confirmed publicly.
2. **Octo (Octobank)** — Uzbek bank acquirer, accepts foreign Visa/Mastercard (~3.5% fee), any service type,
   funds settle in Uzbekistan. Charges in UZS.
3. **Paddle** (merchant of record) — supports Uzbek sellers, charges in JPY/USD, handles tax. Cons: its
   acceptable-use policy forbids pure human services (consultations), so the catalogue would be split.
4. **Stripe** — not available to Uzbek entities; needs a foreign company. Too heavy for now.

## Decision
Ask Rahmat whether it accepts foreign-issued cards. If yes, Rahmat covers all payments. If not, add Octo as
the international provider. Both keep all services in one checkout and the money in Uzbekistan.

## Consequences
- Possibly a second adapter `billing/providers/octo/`, same contract, chosen at checkout by card origin /
  user choice.
- Both providers likely charge in **UZS**: international users pay the UZS price and their bank converts.
  Checkout may show an approximate JPY/USD amount for information only (never charged). Catalog keeps
  one price per currency; a non-UZS price is added only when a provider can actually charge that currency.
- Revisit (Paddle or a foreign entity + Stripe) if foreign card approval rates are poor or JPY pricing
  becomes important.
