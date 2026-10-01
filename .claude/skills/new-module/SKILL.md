---
name: new-module
description: Scaffold a new backend module in the package layout (routers/, services/, repositories/, models/, schemas/, domain/, public.py, tests/) following the modular-monolith conventions, and wire it into the app. Use when adding a new bounded context to backend/app/modules.
argument-hint: <module_name> [short purpose]
---

Create backend module `$ARGUMENTS`. Follow the `modular-monolith` skill; copy the runnable `visa` reference
in `.claude/skills/modular-monolith/templates/app/modules/visa/` and rename.

1. Confirm the name is a snake_case bounded context that doesn't overlap an existing module
   (list `backend/app/modules/`). If it overlaps, stop and propose extending the existing module instead.
   Write its one-line purpose in `__init__.py` and list the aggregates (tables) it will own.
2. Create the package layout:
   ```
   <name>/__init__.py, public.py
   <name>/domain/{__init__,enums,rules,events,exceptions}.py
   <name>/models/{__init__,<aggregate>}.py            # __init__ imports every model
   <name>/repositories/{__init__,<aggregate>_repository}.py
   <name>/schemas/{__init__,<resource>}.py
   <name>/services/{__init__,<use_case>_service}.py
   <name>/routers/{__init__,deps,<resource>}.py       # __init__: APIRouter(prefix="/api/v1/<name>")
   <name>/tests/{__init__,conftest,test_rules,test_<resource>_api}.py
   ```
   Add `providers/`, `handlers/`, `jobs/`, `testing.py` only when needed. Tables prefixed `<name>_`.
3. Register the router in `app/main.py` (`MODULE_ROUTERS`) and any event handlers in `create_app()`.
4. `make importlinter` — regenerates boundary + layer contracts including the new module.
5. Errors are codes (`<name>.<reason>`) added to all four locales (`/translate`); translatable content uses
   `LocalizedText`; money uses `Money`.
6. Tests: domain rules unit test + one API test (happy path, 401, validation code).
7. From `backend/`: `uv run ruff check --fix . && uv run ruff format . && uv run mypy app && uv run lint-imports
   && uv run pytest app/modules/<name>`.
8. If it has tables: `uv run alembic revision --autogenerate -m "<name>: init"`, read and fix it. Don't apply —
   tell the user to run `make migrate`.

Finish with a short summary (in Uzbek): files created, what's next.
