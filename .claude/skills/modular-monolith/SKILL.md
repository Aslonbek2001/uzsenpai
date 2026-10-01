---
name: modular-monolith
description: UzSenpai backend architecture — FastAPI modular monolith with package-based modules (routers/, services/, repositories/, models/, schemas/, domain/, providers/), enforced layers, public facades, domain events and outbox, one transaction per request, error codes, LocalizedText, Money, Postgres-backed tests. Use whenever creating or changing anything under backend/app (modules, core, shared), designing a new module, splitting a large file, or deciding how two modules should talk.
user-invocable: false
paths:
  - "backend/**"
---

# Backend architecture: modular monolith

One deployable FastAPI app, split into **modules = bounded contexts** (list in backend/CLAUDE.md). Each module
owns its tables, logic and API, is internally layered, and is built from small files grouped in packages.

## The rules

1. **Own your data.** A table belongs to one module (prefix `<module>_`). Other modules never query it.
2. **Talk through `public.py`.** The only importable surface: facade class(es) + DTOs (+ re-exported events).
   Tests of other modules may also import `<module>.testing` factories. Enforced by `module-independence`.
3. **Layers inside a module** (enforced by `module-layers`): `testing` → `routers | handlers | jobs` → `public`
   → `services` → `providers` → `schemas | repositories` → `models` → `domain`. Lower never imports higher.
4. **Small files.** Python ≤ 400 lines (tests ≤ 600) — the `size_guard` hook flags a bigger file right after
   it is written and Claude must split it before continuing. Split by
   responsibility: one resource per `routers/<resource>.py` + `schemas/<resource>.py`, one use-case group per
   `services/<name>_service.py`, one aggregate per `models/<x>.py` + `repositories/<x>_repository.py`,
   one external system per `providers/<name>/` package. No `utils.py` dumping grounds.
5. **Sync call vs event.** Need an answer now → facade call. Something happened → domain event.
   Must survive a crash → `durable=True` (outbox) → worker.
6. **One request = one transaction, committed before the response.** Always inject the session as
   `app.core.db.SessionDep` (`Depends(get_session, scope="function")`) — FastAPI then COMMITS before the response
   is sent, so a client/provider never gets 200 for work that failed to commit. Services/repositories never
   commit; routers never touch the session (services come from `routers/deps.py`; import-linter forbids
   `sqlalchemy` in routers). Facades take the caller's session.
7. **Errors are codes** (`AppError("visa.expiry_in_past", params=…)`), translated by clients in uz/ru/en/ja.
8. **Money** is `Money(amount_minor: int, currency)` — never floats, never mixed currencies.

## Package layout of a module

```
modules/<name>/
├── __init__.py          docstring: what this context owns
├── public.py            facade + DTOs for other modules
├── testing.py           (optional) factories for other modules' tests
├── routers/             __init__.py (APIRouter + include_router per resource), deps.py, <resource>.py
├── services/            __init__.py (re-exports), <use_case>_service.py
├── providers/           (optional) <external_system>/ packages behind one Protocol in base.py
├── schemas/             __init__.py (re-exports), <resource>.py
├── repositories/        __init__.py (re-exports), <aggregate>_repository.py
├── models/              __init__.py (imports ALL models for Alembic), <aggregate>.py
├── domain/              enums.py, rules.py | state_machine.py, events.py, exceptions.py — no I/O
├── handlers/ jobs/      (optional) event reactions, Taskiq tasks
└── tests/               conftest.py (module fixtures), test_<rules|domain>.py, test_<resource>_api.py
```

`__init__.py` files re-export the public names of their package, so callers write
`from app.modules.visa.services import VisaStatusService`, never deep paths into sibling files.

## Runnable reference (copy it — it passes ruff, mypy --strict, import-linter and its tests on Postgres)

- [templates/app/main.py](templates/app/main.py) — composition root (`create_app()`, `app = create_app()`)
- [templates/app/core/](templates/app/core/config.py) — `config.py`, `db.py`, `events.py`, `outbox.py`
- [templates/app/shared/](templates/app/shared/errors.py) — `errors.py`, `i18n.py`, `money.py`
- [templates/app/modules/visa/](templates/app/modules/visa/public.py) — complete module in package layout:
  `domain/` (enums, rules, events, exceptions), `models/`, `schemas/`, `repositories/`, `services/`,
  `routers/` (`__init__`, `deps`, `status`), `public.py`, `tests/` (unit + API + outbox)
- [templates/conftest.py](templates/conftest.py) — goes to `backend/conftest.py` (not `tests/`): `app`, `client`,
  `db_session` (per-test rolled-back transaction), `committing_app` (real commits for concurrency /
  commit-before-ack tests, tables emptied after), fake auth via `Authorization: Bearer test-<uuid>`
- Billing/catalog modules with payment providers: the `payments-billing` skill.

`auth.public` must expose `CurrentUser` (with `.id`) and the `current_user` dependency — routers and
`require_entitlement` depend on that contract. `Settings.env` is required (`local|test|staging|production`):
a deployment without `ENV` refuses to start; dev-only features check `settings.is_local`.

## Events and outbox

- `bus.publish(session, event)` queues the event; in-process handlers (`bus.subscribe`) run only after commit.
- `bus.publish(session, event, durable=True)` also writes one `core_outbox` row per durable handler
  (`bus.subscribe_durable(Event, "<module>.<name>", fn)`, `fn(session, event)`) in the same transaction.
  Right after commit a Taskiq task is kicked; a sweeper (every 30 s) is the fallback. 10 attempts with backoff,
  then `dead`; done rows purged after 30 days. The handler's DB writes commit together with the "done" mark;
  external side effects are at-least-once → dedupe by `event.id`. Durable handler names are stored in the DB:
  never rename one while rows may be pending. Code: `app/core/outbox*.py`.
- Subscriptions are registered in `app/wiring.py` (used by both the API and the worker), never in modules.

## Where things go — quick decisions

| Need | Do |
|---|---|
| Module B needs module A's data | `A.public` facade method returning a DTO (add one if missing) |
| Module B must react when A changes | A publishes event (re-exported in `A.public`); B adds `handlers/` |
| B's tests need A's rows | `A.testing` factory (never import A's models in B) |
| New endpoint group | new `routers/<resource>.py` + `schemas/<resource>.py`, included in `routers/__init__.py` |
| Service file growing past ~300 lines | split by use case: `services/<a>_service.py`, `services/<b>_service.py` |
| External API (payment, email, STT) | `providers/<name>/` package implementing a Protocol in `providers/base.py` |
| Shared value type (Money, LocalizedText, Locale) | `app/shared/` (no business logic) |
| Infrastructure (db, redis, settings, bus) | `app/core/` |
| Two modules keep calling each other both ways | boundary is wrong → `architect` subagent + `/adr` |
| Long work (PDF, embeddings, AI batch) | Taskiq task in the module's `jobs/`, triggered via outbox |

After creating a module run `make importlinter` (contracts are generated from the existing modules).

## Testing

- Domain rules: plain unit tests, no DB. Services: with the real DB session or fake facades.
- API: httpx `AsyncClient` against `create_app()`; every endpoint covers happy path, validation (assert the
  code), 401, other user's data → 404, missing entitlement → 403.
- PostgreSQL only (`TEST_DATABASE_URL`) — the per-test SAVEPOINT isolation does not work on SQLite.
- pyproject: `[tool.pytest.ini_options] asyncio_mode = "auto"`, session-scoped loop; ruff
  `line-length = 120`, `[tool.ruff.lint.isort] known-first-party = ["app"]`.
