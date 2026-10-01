---
name: i18n
description: Four-language rules for UzSenpai (uz default, ru, en, ja) across website, bot, backend content, notifications, AI answers and PDFs — key naming, plurals, formatting, glossary of product terms, translation tone per language, review of legal/payment texts. Use whenever adding or changing any user-facing text, locale files, translatable DB content, or anything that depends on the user's language.
user-invocable: false
paths:
  - "frontend/src/**"
  - "bot/**"
  - "backend/app/**"
---

# i18n — uz · ru · en · ja

**Source language is Uzbek.** Write uz first, then ru, en, ja with the same meaning, length budget and tone.
A key is never added to fewer than four locales; `make i18n-check` fails the lint otherwise.

## Where texts live

| Kind | Location | Format |
|---|---|---|
| Website UI | `frontend/src/shared/i18n/locales/{uz,ru,en,ja}/<namespace>.json` | i18next JSON v4, nested keys |
| API error codes → text | namespace `errors` (frontend) / `services/errors.py` msgids (bot) | key = backend code |
| Bot | `bot/locales/{uz,ru,en,ja}/LC_MESSAGES/messages.po` | gettext, English msgid |
| DB content (products, guides, visa pages, lesson meanings) | `LocalizedText` JSONB `{uz,ru,en,ja}` | uz required |
| Emails / push | `backend/app/modules/notifications/templates/<locale>/` | one file per locale |
| PDF resume | Japanese (履歴書/職務経歴書) or English CV — never translated UI chrome | — |

## Keys (frontend)

- Namespaces by area: `common`, `errors`, `nav`, `home`, `career`, `visa`, `learn`, `billing`, `profile`.
- Call syntax `t("ns:key")`: `t("career:resume.step.motivation.title")`. Inside `career.json` the key is
  `resume.step.motivation.title` (no namespace prefix). Backend error codes live in `errors.json` as-is
  (`"visa": {"expiry_in_past": "…"}` ↔ `t("errors:visa.expiry_in_past")`).
- Key = meaning, not the text: `resume.step.motivation.title`, not `why_this_job`.
- Plurals: i18next suffixes. uz/en need `_one` + `_other`; ru needs `_one`, `_few`, `_many`, `_other`;
  ja only `_other`. Always pass `count`.
- Interpolation `{{name}}`; never build sentences by concatenating translated pieces (word order differs).
- Japanese embedded in a non-ja sentence (e.g. `履歴書`) stays in the text and is wrapped with `lang="ja"` in UI.

## Formatting

Dates/numbers/money only via `Intl` (frontend `fmt.*`, backend Babel for emails). Money from the API is
integer minor units + ISO currency (`{amount_minor, currency}`) — UZS for national, USD/JPY/EUR for
international checkout; display with `fmt.money(amount_minor, currency, locale)`. Locale tags: `uz-Latn-UZ`, `ru-RU`, `en-US`, `ja-JP`.

## Tone per language

- **uz** — Latin script, `oʻ gʻ` with U+02BB, tutuq belgisi `’`; "siz" form; short, warm, plain words.
- **ru** — «вы» lowercase in UI, neutral-friendly; avoid bureaucratic phrasing; expect +30% length.
- **en** — plain English, sentence case, contractions OK.
- **ja** — polite です・ます, standard UI wording (保存, 次へ, キャンセル); kanji for nouns, avoid long katakana
  chains; no romaji in UI.

## Glossary — use these exact terms

See [glossary.md](glossary.md). Add a term there before using a new product word in four languages.

## Review

Strings in `billing`, `visa`, legal/terms and anything about money or refunds must be reviewed by a native
speaker before release: list new/changed keys in `docs/i18n-review.md` (key, languages to review). Claude's
translations are allowed for everything else.

## Backend & AI

- Errors return codes (`resume.photo_too_large`), never sentences.
- Pass `locale` explicitly to `ai.public` calls; the system prompt states the answer language. Resume text
  output is Japanese, explanations in the user's locale.
- RAG answers cite sources in their original language and explain in the user's locale.
