# UzSenpai — technology stack (source of truth)

Claude: **never introduce a language, framework, library, service or provider that is not listed here
without asking the user first.** If something is needed, propose it with the reason and the alternative
already in the stack, wait for a yes, then add it to this file in the same change.
Section 3 items are not chosen yet — don't write code that depends on them without an ADR.

## 1. Chosen by the owner (fixed — do not change)

| Area | Choice |
|---|---|
| Repository | One monorepo: `frontend/`, `backend/`, `bot/` (+ `infra/`, `docs/`) |
| Frontend | React |
| Backend | FastAPI (Python) |
| Telegram bot | aiogram (v3) |
| Backend architecture | Modular monolith |
| AI | LLM via Anthropic API (Claude) + RAG |
| Languages (site + bot) | Uzbek (`uz`, default), Russian (`ru`), English (`en`), Japanese (`ja`) |
| Product | Paid services platform: Japanese resume, interview prep, visa info/consultations, life-in-Japan guides; Japanese learning is one section |
| Devices | Mobile, tablet and desktop — 100% responsive |
| Payments | National (Uzbekistan, UZS) **and** international payment systems |
| Code organisation | Senior-level structure: modules split into packages (`routers/`, `services/`, `repositories/`, `models/`, `schemas/`, `domain/`), no huge files |

## 2. Confirmed by the owner (2026-10-02)

| Area | Choice |
|---|---|
| Frontend language / build | TypeScript (strict), Vite |
| Frontend libraries | React Router, TanStack Query, Zustand (UI state only), React Hook Form + Zod, Tailwind CSS v4, Radix UI primitives, `motion`, lucide-react, i18next + react-i18next, vite-plugin-pwa |
| Frontend tooling | pnpm (via corepack), ESLint, Prettier, Vitest + Testing Library, openapi-typescript (API types from FastAPI OpenAPI), @hookform/resolvers |
| Python tooling | Python 3.13, uv, ruff, mypy, pytest + pytest-asyncio, import-linter |
| Database | PostgreSQL 17 + pgvector extension and `pgvector` Python package (one DB for app data and RAG vectors) |
| ORM / migrations | SQLAlchemy 2.x async (currently 2.1) + asyncpg, Alembic |
| Cache / queues | Redis; background tasks with **Taskiq** (`taskiq` + `taskiq-redis`) — [ADR 0001](adr/0001-taskiq-for-background-tasks.md) |
| Auth | Short-lived JWT access token (memory) + rotating refresh token in an httpOnly cookie, Telegram Login, argon2 password hashing (argon2-cffi) |
| Embeddings (RAG) | Voyage AI (Anthropic has no embeddings API) behind an `EmbeddingProvider` interface; ranking = reciprocal-rank fusion (no reranker) |
| National payments (UZS) | **Rahmat** (rhmt.uz) — one integration covers Humo, Uzcard, Visa/Mastercard and Click/Payme/Uzum wallets; adapter in `billing/providers/rahmat/` — [ADR 0002](adr/0002-rahmat-national-payments.md). Integration waits for merchant docs; prep in [docs/payments/rahmat.md](payments/rahmat.md) |
| File storage | S3-compatible object storage via aioboto3 in staging/prod; local-disk adapter in local dev (no extra compose service) |
| Bot i18n | aiogram built-in i18n (gettext `.po` files, Babel) |
| Uzbek spelling | Latin script, `oʻ gʻ` with U+02BB and `’` (U+2019) as tutuq belgisi; user input and search normalise `o' o` o‘` etc. to the canonical form |
| International payments | Rahmat first (if it accepts foreign-issued cards); otherwise **Octo** (Octobank) as a second provider — [ADR 0003](adr/0003-international-payments.md) |
| Payments inside the Telegram bot | No in-bot payments: the bot opens website checkout (Mini App / link) — [ADR 0004](adr/0004-bot-payments-via-website-checkout.md) |
| PDF generation | Headless Chromium via Playwright (Python) in the worker: HTML template → A4 PDF, Japanese fonts embedded — [ADR 0005](adr/0005-pdf-rendering-headless-chromium.md) |
| Email | Resend (delivery) + Jinja2 templates per locale + Babel for date/number formatting |
| Hosting / reverse proxy | VPS abroad (e.g. Hetzner) + Caddy (automatic HTTPS) — [ADR 0006](adr/0006-hosting-abroad-with-caddy.md); personal-data localization risk accepted, see the ADR |
| FastAPI version | ≥ 0.121 (needed for `Depends(..., scope="function")` — commit before the response) |
| Local infra | Docker Compose |
| UI testing | Playwright MCP, pinned `@playwright/mcp@0.0.83` in `.mcp.json` (bump deliberately) |
| Design system | "Sumi & Ai" (frontend/DESIGN.md) — fonts Onest, Zen Kaku Gothic New, Klee One, **self-hosted** woff2 (no Google Fonts requests) |

## 3. Open decisions (each needs an ADR before code depends on it)

| Area | Status |
|---|---|
| Speech-to-text (interview voice mode) | postponed — text interview first; ADR when voice mode is built (Japanese quality, price, privacy) |

## 4. Explicitly not used (unless the owner changes this file)

- No other LLM providers (OpenAI, Gemini…) and no LangChain/LlamaIndex — call the Anthropic SDK directly.
- No separate vector database (Pinecone, Qdrant…) — pgvector.
- No microservices, no message broker besides Redis.
- No CSS-in-JS, no UI kits with their own visual style (MUI, Ant, Chakra, Bootstrap).
- No Next.js / SSR framework (React SPA + PWA).
