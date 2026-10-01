# UzSenpai — technology stack (source of truth)

Claude: **never introduce a language, framework, library, service or provider that is not listed here
without asking the user first.** If something is needed, propose it with the reason and the alternative
already in the stack, wait for a yes, then add it to this file in the same change.
Items marked ❓ are assumptions — follow them, but if a task depends heavily on one, mention it.

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

## 2. Assumed by Claude during setup (❓ confirm or replace)

| Area | Current assumption |
|---|---|
| Frontend language / build | ❓ TypeScript (strict), Vite |
| Frontend libraries | ❓ React Router, TanStack Query, Zustand (UI state only), React Hook Form + Zod, Tailwind CSS v4, Radix UI primitives, `motion`, lucide-react, i18next + react-i18next, vite-plugin-pwa |
| Frontend tooling | ❓ pnpm, ESLint, Prettier, Vitest + Testing Library, openapi-typescript (API types from FastAPI OpenAPI), @hookform/resolvers |
| Python tooling | ❓ Python 3.12, uv, ruff, mypy, pytest + pytest-asyncio, import-linter |
| FastAPI version | ❓ ≥ 0.121 (needed for `Depends(..., scope="function")` — commit before the response) |
| Database | ❓ PostgreSQL 16 + pgvector extension and `pgvector` Python package (one DB for app data and RAG vectors) |
| ORM / migrations | ❓ SQLAlchemy 2.0 async + asyncpg, Alembic |
| Cache / queues | ❓ Redis; background jobs with arq |
| Embeddings (RAG) | ❓ Voyage AI (Anthropic has no embeddings API) behind an `EmbeddingProvider` interface; ranking = reciprocal-rank fusion (no reranker) |
| National payments (UZS) | ❓ Click, Payme, Uzum — adapters in `billing/providers/` |
| International payments (USD/JPY/EUR) | **undecided** — candidates to evaluate by ADR (e.g. Stripe, Paddle); plugs into the same `PaymentProvider` contract |
| File storage | ❓ S3-compatible object storage |
| PDF generation | ❓ HTML template → PDF in the worker (library to be chosen when the resume module is built) |
| Auth | ❓ JWT access + refresh tokens, Telegram Login, argon2 password hashing (argon2-cffi) |
| Email / templates | ❓ Jinja2 templates per locale + Babel for date/number formatting; email delivery provider **undecided** |
| Object storage client | ❓ S3-compatible via aioboto3 |
| Speech-to-text (interview voice mode) | **undecided** — voice mode waits for an ADR |
| Reverse proxy / hosting | **undecided** |
| Bot i18n | ❓ aiogram built-in i18n (gettext `.po` files, Babel) |
| Payments inside the Telegram bot | **open decision** — Telegram requires Telegram Stars for digital goods/services sold in bots; until an ADR decides, the bot links to website checkout |
| Local infra | ❓ Docker Compose |
| UI testing | ❓ Playwright MCP (`@playwright/mcp`) for visual checks — pin a version once the frontend exists |
| Design system | ❓ "Sumi & Ai" (frontend/DESIGN.md) — fonts Onest, Zen Kaku Gothic New, Klee One, **self-hosted** woff2 (no Google Fonts requests) |
| Uzbek spelling | ❓ Latin script, `oʻ gʻ` with U+02BB and `’` (U+2019) as tutuq belgisi |

## 3. Explicitly not used (unless the owner changes this file)

- No other LLM providers (OpenAI, Gemini…) and no LangChain/LlamaIndex — call the Anthropic SDK directly.
- No separate vector database (Pinecone, Qdrant…) — pgvector.
- No microservices, no message broker besides Redis.
- No CSS-in-JS, no UI kits with their own visual style (MUI, Ant, Chakra, Bootstrap).
- No Next.js / SSR framework (React SPA + PWA).
