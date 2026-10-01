---
name: frontend-architecture
description: UzSenpai frontend architecture — React SPA with Feature-Sliced Design, typed API client over generated OpenAPI types, TanStack Query patterns (query keys, mutations, optimistic updates, SSE), React Router (lazy routes, scroll restoration), i18next with uz/ru/en/ja, forms with React Hook Form + Zod, error codes, entitlement-gated paid features. Use whenever creating or changing code under frontend/src (not just visuals — for visuals also follow frontend/DESIGN.md).
user-invocable: false
paths:
  - "frontend/**"
---

# Frontend architecture

## Layers (Feature-Sliced Design)

`app → pages → widgets → features → entities → shared` — a layer imports only from layers to its right.
Each slice exposes `index.ts`; import `@/entities/order`, never `@/entities/order/model/useOrder`.
Inside a slice: `ui/` (one component per file), `model/` (hooks/state), `api/` (queries/mutations), `lib/`
(pure helpers). Files ≤ 300 lines (`size_guard` hook).

| Layer | Holds | Example |
|---|---|---|
| `app/` | providers, router, i18n init, global CSS | `app/router.tsx`, `app/providers.tsx` |
| `pages/` | route screens, compose lower layers, no business logic | `pages/career/resume-step` |
| `widgets/` | big self-contained blocks | `widgets/app-shell`, `widgets/interview-chat` |
| `features/` | one user action each (mutation + its UI) | `features/checkout-pay`, `features/switch-language` |
| `entities/` | domain read models: query hooks, small UI | `entities/order` (`useOrder`, `OrderStatusBadge`) |
| `shared/` | ui kit, api client, i18n, lib, config — no domain words | `shared/api/client.ts` |

## Data

- One API client (`shared/api/client.ts`) built on generated types: sends `Accept-Language` = current locale,
  auth header, and turns `{"error":{"code","params"}}` into `ApiError(code, params)`.
- Server state only in TanStack Query. Query keys from a factory per entity (`orderKeys.detail(id)`).
- Lists/pagination: `placeholderData: keepPreviousData` (no layout jump). Prefetch on hover/touchstart.
- Mutations invalidate exactly the keys they affect; optimistic updates for toggles/ticks/SRS answers.
- AI streams (interview, resume translate, tutor): `fetch` + `ReadableStream` SSE parser in `shared/api/sse.ts`,
  abort on unmount, show partial text, keep the user's input on error.
- Locale change → `i18n.changeLanguage` + `PATCH /users/me {locale}` + `queryClient.invalidateQueries()`
  (server returns localized content).

## Errors

`ApiError.code` → `t('errors:<code>', params)` (namespace `errors` in all four locales). Unknown code →
`errors:common.unknown`. Never show raw server text. Field errors map to the form.

**Key syntax everywhere: `t("ns:key.path")`** (`t("visa:form.save")`). Keys inside `visa.json` carry no
namespace prefix. Namespaces load lazily through the i18n backend in `shared/i18n` (Suspense), so a new
namespace only needs its four JSON files.

## Paid features

`useEntitlement('resume.pdf_export')` reads `GET /billing/entitlements`. Locked → `<PaywallCard product=…/>`
(what you get, price from API, button → checkout). Server still enforces — UI gating is only UX.

## Routing

Lazy route modules, skeleton fallback the same size as the page, `<ScrollRestoration />` in the root layout,
`preventScrollReset` on tab/filter links. Route paths are not translated; content is.

## Templates

- [templates/client.ts](templates/client.ts) — API client + `ApiError`
- [templates/queries.ts](templates/queries.ts) — query key factory, query + optimistic mutation
- [templates/i18n.ts](templates/i18n.ts) — i18next with uz/ru/en/ja, lazy namespaces, `Intl` formatters
- [templates/router.tsx](templates/router.tsx) — lazy routes, scroll restoration, app shell
- [templates/form.tsx](templates/form.tsx) — RHF + Zod with translated errors and server error codes
- [templates/entitlement.tsx](templates/entitlement.tsx) — paywall gate

## Testing

Vitest + Testing Library; mock the API client, not `fetch` internals. Each feature test renders in all four
locales at least once for overflow-prone UI (buttons, tabs) via a `renderWithLocale` helper.
