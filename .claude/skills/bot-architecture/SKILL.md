---
name: bot-architecture
description: UzSenpai Telegram bot architecture on aiogram 3 — thin client of the backend; routers per feature, middlewares (backend user, locale, throttling), gettext i18n in uz/ru/en/ja with a language picker, CallbackData factories, FSM flows in Redis, typed httpx backend client, paid-service checkout links and order status, webhook vs polling. Use whenever creating or changing code under bot/.
user-invocable: false
paths:
  - "bot/**"
---

# Bot architecture (aiogram 3)

The bot is a **client**, like the website. It never touches the DB or Anthropic; everything goes through
`services/api_client.py` to the backend with a service token + the Telegram user id.

## Request flow

```
Update → ThrottlingMiddleware → BackendUserMiddleware (get/create user via `users` module's
       /api/v1/bot/users, cached 60 s; put `user` + `locale` in data)
       → UzI18nMiddleware (locale from data) → Router(feature) → handler → api_client → backend
```

## Rules

- One feature = one `Router` (`handlers/<feature>.py`, or a `handlers/<feature>/` package with one file per
  step when it grows), included in `main.py` in a fixed order (`start`, `language`, `menu`, then features,
  `fallback` last). Files ≤ 400 lines.
- Every text: `_("…")` at call time, `__("…")` for module-level constants (keyboards). Source strings are
  English msgids; translations live in `locales/{uz,ru,en,ja}/LC_MESSAGES/messages.po`. `make i18n-bot`
  extracts/updates, `make i18n-check` fails on any untranslated string.
- Language: first `/start` → guess from `message.from_user.language_code` (uz/ru/en/ja else uz), save to the
  backend, show the picker once. `/language` any time. Language names in their own language, no flags.
- `bot.set_my_commands(..., language_code=<lang>)` for each of the four at startup, plus a default list
  (no language_code) for Telegram clients in other languages.
- Callback data only via `CallbackData` factories; keyboards built in `keyboards/`.
- FSM states for multi-step flows (resume quick-start, visa status input), Redis storage, always a
  cancel button.
- Paid services: list products from `GET /api/v1/catalog/products?currency=UZS` (localized by backend). How the
  bot takes payment is an **open decision** (docs/STACK.md): Telegram requires Telegram Stars for digital
  goods sold inside bots, so until an ADR decides, the bot only links to the website checkout and never
  shows provider invoices. Order status messages are sent by the backend `notifications` module.
- AI answers: backend streaming endpoint → edit message at most ~1/sec; final edit with the full text.
- Errors: api_client raises `BackendError(code, params)`; handlers reply `error_text(err)` from
  `services/errors.py` — a dict of backend code → `__("English msgid")` (static, so pybabel extracts it).
  Never build msgids at runtime, never show raw backend text. New backend code → add it there + `/translate`.

## Templates

- [templates/main.py](templates/main.py) — dispatcher, middlewares, routers, commands per language, polling/webhook
- [templates/middlewares.py](templates/middlewares.py) — backend user + locale middleware
- [templates/language.py](templates/language.py) — language picker with CallbackData (`start.py` sketch at the bottom)
- [templates/api_client.py](templates/api_client.py) — typed backend client, error codes
- [templates/errors.py](templates/errors.py) — backend error code → translated text

## Testing

Unit-test handlers by calling them with fake `Message`/`CallbackQuery` objects (or `AsyncMock`s) and a mocked
api_client;
assert on the text in **each** of the four locales for at least the start/language flow.
