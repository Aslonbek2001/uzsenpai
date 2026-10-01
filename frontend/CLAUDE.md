# Frontend — React

Stack (see docs/STACK.md): React 19, Vite, TypeScript (strict), React Router, TanStack Query, Zustand (client UI
state only), React Hook Form + Zod, Tailwind CSS v4, Radix UI primitives, `motion` (motion/react), lucide-react,
i18next + react-i18next, vite-plugin-pwa. Package manager: **pnpm**.
Architecture details and code templates: the `frontend-architecture` skill. Languages: the `i18n` skill.

## Design — read before any UI work

@DESIGN.md

- Tokens: `src/shared/ui/theme/tokens.css` · motion presets: `src/shared/ui/theme/motion.ts`
- Interaction reference component: `src/shared/ui/button/Button.tsx`
- New screen → `/new-page` (uses the `ui-designer` subagent). New building block → `/new-component`.
- After UI changes → `/ui-audit <route>` (the `ux-reviewer` subagent tests 360 / 768 / 1440 in a real browser).
- Plain-looking screen → `/ui-polish`.

## Structure (Feature-Sliced Design)

```
frontend/src/
├── app/          # providers, router, global styles, query client, i18n init
├── pages/        # route-level screens: home, career/*, visa/*, learn/*, profile/*, checkout
├── widgets/      # large blocks: app-shell (tab bar / rail / sidebar), resume-preview, interview-chat, order-timeline
├── features/     # user actions: auth-login, resume-translate, interview-answer, checkout-pay, srs-review, switch-language
├── entities/     # domain objects: user, resume, interview, order, product, visa-status, guide, lesson, kanji
└── shared/       # ui kit, lib, config, i18n (locales), api (client + generated types)
```

Import direction only downward: app → pages → widgets → features → entities → shared.
A slice exposes its public API through its `index.ts`; import from the slice root, never deep paths.

Every slice is split into segments — never one big file:

```
features/checkout-pay/
├── index.ts          # public API of the slice
├── ui/               # one component per file: CheckoutSheet.tsx, ProviderPicker.tsx, PriceSummary.tsx
├── model/            # hooks + local state: useCheckout.ts, useProviderChoice.ts
├── api/              # queries/mutations: checkout.ts (uses shared/api client + generated types)
└── lib/              # pure helpers: currency.ts (+ tests next to them)
```

File size (enforced by the `size_guard` hook): `.ts/.tsx` ≤ 300 lines (tests ≤ 500). Over it → extract
sub-components into `ui/`, hooks into `model/`, helpers into `lib/`.

## Rules

- Server state = TanStack Query only. Don't copy server data into Zustand.
- API: typed client in `shared/api/` built on the generated types (`make api-types`). Never hand-write types
  the backend already defines. Never edit generated files.
- No secrets in the frontend. Only `VITE_*` public config. No prices in frontend code — they come from the API.
- **4 languages:** all visible text via `t('...')`; keys in `shared/i18n/locales/{uz,ru,en,ja}/<namespace>.json`,
  added to all four at once. Dates, numbers and money via `Intl` with the current locale. Japanese learning
  content (kana/kanji/furigana) comes from the API, not from i18n files.
- AI features (tutor, interview, resume translate) consume backend SSE streams; render incrementally, handle abort/retry.
- Paid features: UI asks the API for entitlements; locked state shows what the user gets and the price — never
  hide it behind an error.
- Components: function components, named exports, props typed with `type`, no `any`.
- Accessibility: semantic elements, labels on inputs, keyboard navigable. Mobile-first — most users are on phones.

## Commands (from frontend/)

```
pnpm dev
pnpm lint          # eslint
pnpm typecheck     # tsc --noEmit
pnpm test          # vitest + Testing Library
pnpm build
```
