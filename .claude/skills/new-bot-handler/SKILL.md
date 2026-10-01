---
name: new-bot-handler
description: Add a new aiogram 3 feature to the Telegram bot — Router, keyboards, CallbackData, FSM states, locale texts and backend API client methods. Use when adding a bot command or multi-step flow.
argument-hint: <feature_name> <what the flow does>
---

Add bot feature: $ARGUMENTS

1. Read `bot/CLAUDE.md` and the `bot-architecture` skill; copy its templates (or an existing handler).
2. If the flow needs data the backend doesn't expose yet, stop and list the endpoints needed
   (they should be built with `/new-endpoint` first). The bot never reads the DB.
3. Add typed methods to `bot/app/services/api_client.py`.
4. Create `handlers/<feature>.py` with its own `Router` — or a `handlers/<feature>/` package (one file per
   step, `__init__.py` builds the feature Router) for multi-step flows; `keyboards/<feature>.py` with `CallbackData`
   factories; `states/<feature>.py` if multi-step.
5. Every user-facing string via `_()`; run `make i18n-bot`, then fill uz, ru, en, ja in the `.po` files
   (`/translate`). `make i18n-check` must pass.
6. Register the router in `main.py`.
7. Tests with a mocked api_client. Run `uv run pytest -q && uv run ruff check --fix . && uv run mypy app`.
