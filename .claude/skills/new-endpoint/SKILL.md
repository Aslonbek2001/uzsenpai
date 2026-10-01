---
name: new-endpoint
description: Add a backend API endpoint end-to-end in the package layout — schemas/<resource>.py, domain rules, repository, services/<use_case>_service.py, routers/<resource>.py, tests — then regenerate the frontend API types. Use when a feature needs a new or changed /api/v1 route.
argument-hint: <module> <METHOD /path> <what it does>
---

Add endpoint: $ARGUMENTS

1. Read `backend/CLAUDE.md` and the target module's packages. Decide where it belongs:
   existing resource → its `routers/<resource>.py`; new resource → new `routers/<resource>.py` +
   `schemas/<resource>.py`, included in `routers/__init__.py`.
2. Schemas first (`schemas/<resource>.py`, re-exported from `schemas/__init__.py`).
3. Pure rules in `domain/` (testable without DB) → repository method in `repositories/` → service method in the
   matching `services/<use_case>_service.py` (new file if it's a different use-case group or the file would pass
   ~300 lines) → thin route with `response_model=` and proper status codes. Services come from `routers/deps.py`;
   routes never touch the session.
   Paid feature → `dependencies=[Depends(require_entitlement(Key.X))]`; quota consumed after success.
   Authorization: users only access their own data (not found → 404, not 403, to avoid leaking existence).
4. Errors: exception classes in `domain/exceptions.py` with code `<module>.<reason>` — never a sentence, never
   `HTTPException` in services. Add the code to the frontend `errors` namespace in all four locales and to the
   bot's `services/errors.py` if the bot can hit it (`/translate`). Localized content uses
   `LocalizedText.resolve(locale)`; money uses `Money`.
5. Tests: happy path, validation (assert the code), 401, other user's data → 404, missing entitlement → 403.
6. From `backend/`: `uv run pytest app/modules/<module> && uv run lint-imports && uv run mypy app`.
7. `make api-types`; say which frontend `entities/<x>/api` hook should use it.
