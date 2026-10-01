# Bot — Telegram, aiogram 3

Python 3.13, aiogram 3.x, httpx (backend client), Redis FSM storage, pydantic-settings. Package manager: **uv**.
Architecture details and code templates: the `bot-architecture` skill. Languages: the `i18n` skill.

The bot is a **thin client of the backend**. It never opens a DB connection and never calls Anthropic.
Everything (users, resume, interview, visa, orders, payments, lessons) goes through `services/api_client.py`
→ backend `/api/v1`.

## Structure

```
bot/app/
├── main.py            # Bot, Dispatcher, middlewares, router registration, startup/shutdown
├── config.py          # settings (BOT_TOKEN, BACKEND_URL, BACKEND_SERVICE_TOKEN, REDIS_URL, WEBHOOK_*)
├── handlers/          # one Router per feature: start, language, menu, resume, interview, visa, orders, learning
├── keyboards/         # inline/reply keyboard builders + CallbackData factories
├── states/            # FSM StatesGroup per flow
├── middlewares/       # backend-user resolution, i18n (locale per user), throttling, error reporting
├── filters/
├── services/
│   ├── api_client.py  # typed httpx.AsyncClient wrapper around backend endpoints
│   └── errors.py      # backend error code → translated text
bot/locales/           # {uz,ru,en,ja}/LC_MESSAGES/messages.po (gettext via aiogram i18n + Babel)
```

## Rules

- One feature = one `Router`. Small feature: `handlers/<feature>.py`. Feature with several steps or screens:
  a package — `handlers/<feature>/__init__.py` (builds the feature `Router` and includes sub-routers),
  `handlers/<feature>/<step>.py` per step, matching `keyboards/<feature>.py` and `states/<feature>.py`.
  Python files ≤ 400 lines (the `size_guard` hook enforces it).
- Callback data via `CallbackData` factories, never raw strings parsed by hand.
- Multi-step flows use FSM states (`states/`), storage in Redis.
- **4 languages (uz, ru, en, ja):** every text through `_()` / `__()` from `locales/`. On first `/start` the
  language is guessed from Telegram's `language_code` (fallback `uz`) and the user is offered a picker;
  `/language` changes it any time and saves it to the backend profile (shared with the website).
  Commands menu (`set_my_commands`) is registered for each language.
- Paid services: the bot never shows hard-coded prices; it gets products from the backend and links to the
  website checkout. No in-bot payments (ADR 0004): no provider invoices,
  no Telegram Stars.
- AI answers: call the backend streaming endpoint and edit the message in chunks (throttle to ~1 edit/sec).
- Long-running work never blocks a handler; the backend does it and its `notifications` module messages the
  user directly through the Telegram Bot API (the bot process is not involved).
- Webhook mode in production, polling in local dev.

## Commands (from bot/)

```
uv run python -m app.main
uv run pytest -q
uv run ruff check --fix . && uv run ruff format .
uv run mypy app
make i18n-bot-init     # first time: create the four catalogs (from repo root)
make i18n-bot          # extract (-k __ for lazy strings) → update → compile (from repo root)
```
