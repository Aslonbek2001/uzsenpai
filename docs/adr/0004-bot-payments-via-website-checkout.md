# 0004. Telegram bot payments go through website checkout

- Status: accepted
- Date: 2026-10-02

## Context
The bot sells the same paid services as the website. Telegram requires Telegram Stars for digital goods and
services sold inside bots; Stars carry a large platform cut and awkward payouts. Human services and
digital services are mixed in the catalogue.

## Options
1. **Bot opens website checkout** (Mini App or link) — one checkout, one set of providers, Telegram-compliant.
2. **Telegram Stars** for digital items — native UX, but ~30% cost and a second payment system.
3. **Both** — Stars for digital, website for the rest. Two systems to maintain.

## Decision
The bot never takes payment itself. "Pay" in the bot opens the website checkout for the same product and
currency; entitlements are shared because the account is shared.

## Consequences
- Bot needs a deep link / Mini App URL to checkout with `product_id`; the result comes back via the backend
  (entitlement granted → bot notified through `notifications`).
- No Stars integration. Revisit if Telegram policy changes or conversion in the bot is too low.
