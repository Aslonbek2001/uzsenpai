---
name: new-service
description: Add a new paid service end-to-end — catalogue product and price, entitlement keys, backend feature gated by entitlement (AI or human-fulfilled order), checkout and status UI, bot entry point, and tests. Use when the user wants to sell something new (e.g. document translation, cover letter, consultation type).
argument-hint: <service name> <what the customer gets> [ai|human] [one-off|quota|subscription]
disable-model-invocation: true
---

New paid service: $ARGUMENTS

Read `backend/CLAUDE.md` → "Paid services" and `frontend/DESIGN.md` §9 "Paid services — trust patterns" first.

1. **Plan (show it before coding):** customer-facing name and bullets in uz (ru/en/ja via `/translate`;
   catalog texts are `LocalizedText`, billing texts go to `docs/i18n-review.md`), the problem it solves, what exactly they get
   (3–5 bullets), delivery time, AI or human fulfilment, pricing model, entitlement key(s), refund rule.
   Prices are product decisions — ask the user for the amount; never invent one.
2. **catalog:** add the product, one price row per currency it is sold in (UZS for national checkout;
   USD/JPY/EUR if sold internationally — amounts in minor units, given by the user), and its grants using keys
   from `catalog/domain/keys.py`.
3. **Feature module** (existing, or `/new-module` if new): endpoints gated with `require_entitlement("<key>")`.
   - AI service: consume quota only after a successful result.
   - Human service: create an `orders` order on payment; status workflow, expert assignment, deliverable via
     `files`, notifications on each status change.
4. **billing:** make sure the product is purchasable through the existing checkout (no provider-specific code
   in the feature module).
5. **Frontend:** service card (what you get, time, price, refund terms) → checkout sheet → result/order
   status screen, in the right `data-space`; delegate the screens to `ui-designer`, then `/ui-audit`.
6. **Bot:** entry point that deep-links to checkout or shows order status (`/new-bot-handler`).
7. **Tests:** cannot access without entitlement (403), access after payment webhook, idempotent webhook,
   quota not consumed on failure, order status transitions.
8. Run `/backend-review <module>` and `/check`. Report in Uzbek.
