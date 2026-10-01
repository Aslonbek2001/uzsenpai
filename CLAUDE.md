# UzSenpai

Paid services platform for Uzbek speakers going to / living in Japan. Product areas:

1. **Career** (core, paid): Japanese resume builder (履歴書 / 職務経歴書), AI mock interviews, expert review.
2. **Visa & life in Japan** (paid + free): visa info and eligibility, document checklists, expiry reminders,
   expert consultations, sourced life guides.
3. **Learning** (one section): Japanese lessons, kanji, SRS, JLPT mock tests, AI tutor.

Money flows through `catalog` → `billing` (entitlements) → `orders`. Solo-developer monorepo.

**Talk to the user in Uzbek.** Code, comments, commit messages and identifiers in English.

## Stack — only what's in docs/STACK.md

@docs/STACK.md

## Languages — 4 everywhere

Site and bot support **uz (default) · ru · en · ja**. No user-facing string is hardcoded; every new key is
added to all four locales in the same change (`make i18n-check` fails otherwise). Backend returns error
*codes*, clients translate them. Details: the `i18n` skill.

## Repo layout

```
backend/    FastAPI modular monolith — the ONLY owner of the database and the Anthropic API
frontend/   React SPA (talks to backend over HTTP only)
bot/        Telegram bot on aiogram 3 (talks to backend over HTTP only)
compose.yaml  docker compose for local dev (repo root, works from any subfolder)
infra/      deploy scripts (reverse proxy / hosting: see docs/STACK.md)
docs/       STACK.md, ADRs (docs/adr/NNNN-title.md), provider prep notes (docs/payments/)
scripts/    repo-wide checks (i18n)
```

Each app folder has its own CLAUDE.md — read it before working there.

## Architecture rules (non-negotiable)

1. **Backend is the single source of truth.** Frontend and bot never touch Postgres or the Anthropic API.
   If they need data or AI, add/extend a backend endpoint. The bot uses Redis only for its own FSM/throttling
   state (separate Redis DB index).
2. **Senior-level structure, no giant files.** Every backend module is a set of packages (`routers/`,
   `services/`, `repositories/`, `models/`, `schemas/`, `domain/`, optional `providers/`) with enforced layers;
   frontend slices use `ui/ model/ api/ lib/`; bot features become `handlers/<feature>/` packages.
   Python ≤ 400 lines, TS/TSX ≤ 300 lines per file (`size_guard` hook).
3. **Modular monolith.** Backend modules talk to each other only through the other module's
   `public.py` facade or domain events. `import-linter` enforces this (`make lint`; contracts are generated
   from the existing modules by `scripts/sync_importlinter.py`).
4. **API contract first.** Backend OpenAPI schema → generated TS types in `frontend/src/shared/api/generated/`
   (`make api-types`). Never hand-edit generated files.
5. **Access to paid features only through entitlements** (`billing.public`). Prices live only in `catalog` (one price per currency; national UZS + international).
6. **Secrets** only via env vars (`.env`, never committed). Each app has its own `.env.example`.
7. Decisions that change a boundary, add infra or change docs/STACK.md → short ADR via `/adr`.
8. **Apps build and deploy independently.** Each app has its own lockfile (`uv.lock` / `pnpm-lock.yaml`),
   `Dockerfile` with its own folder as build context, `.dockerignore`, `.env.example` and Makefile targets
   (`lint-<app>`, `test-<app>`). No root-level workspace, no code imported across app folders — the only shared
   contract is the backend OpenAPI schema (`/api/v1`, changes stay backward compatible so the bot and frontend
   can deploy on their own schedule). A bot change rebuilds and redeploys only the bot.

## Architecture knowledge (skills load automatically when relevant)

| Skill | Covers |
|---|---|
| `modular-monolith` | package-based module layout, enforced layers, facades, events, DB/session, errors — runnable reference |
| `frontend-architecture` | Feature-Sliced structure, API layer, queries, routing, forms, errors |
| `bot-architecture` | aiogram routers, middlewares, FSM, callback data, backend client |
| `i18n` | 4-language rules for frontend, bot, backend content, AI and PDFs |
| `payments-billing` | national + international providers, Money, catalog → checkout → webhooks → entitlements → orders |
| `llm-rag` | Anthropic SDK usage, prompts, caching, streaming, RAG pipeline, evals |

## Commands (run from repo root)

```
make up            # docker compose: postgres(pgvector), redis, backend, worker (Taskiq), frontend, bot
make down
make lint          # ruff + mypy + import-linter (backend, bot), eslint + tsc (frontend), i18n check
make test          # all tests
make i18n-check    # every key present in uz, ru, en, ja (frontend + bot)
make i18n-bot      # re-extract bot strings into the four .po files (first time: make i18n-bot-init)
make importlinter  # regenerate module-boundary contracts (also runs in make lint)
make migrate       # alembic upgrade head
make api-types     # regenerate frontend API types from backend OpenAPI
```

## Workflow

- Small, focused changes. Before saying a task is done, run `make lint` and the relevant tests.
- New backend module → `/new-module`. New endpoint → `/new-endpoint`. New paid service → `/new-service`.
  New bot flow → `/new-bot-handler`. New page → `/new-page`. New UI building block → `/new-component`.
  Texts/translations → `/translate`. Architecture decision → `/adr`.
- Cross-cutting or boundary-touching change → ask the `architect` subagent to review the plan first.
- Any UI work follows `frontend/DESIGN.md`; verify with `/ui-audit` at 360 / 768 / 1440 px.
- Before releasing a backend module → `/backend-review` (architect + security-auditor + db-performance).
- Quality gate → `/check`. Commit → `/commit` (Conventional Commits, scope = app or module).
- Don't add a dependency that isn't in docs/STACK.md — ask first (`uv add` / `pnpm add` always prompt).
