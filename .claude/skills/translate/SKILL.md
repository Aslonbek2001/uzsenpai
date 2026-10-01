---
name: translate
description: Add or update user-facing texts for a feature in all four languages (uz, ru, en, ja) — frontend locale JSON, bot .po files and LocalizedText seeds — following the glossary and tone rules, then run the i18n check. Use when the user says "tarjima", "translate", "matnlarni qo'sh", or after building UI/bot features with new strings.
argument-hint: <feature / namespace / file> [uz texts if already written]
---

Translate: $ARGUMENTS

1. Load the `i18n` skill rules and [glossary](../i18n/glossary.md).
2. Find the new/changed strings: `t('…')` keys missing from locale files, `_("…")` msgids missing from `.po`
   (run `make i18n-bot` to extract), `LocalizedText` seeds with empty languages.
3. Write **uz first** (or use the user's uz text as-is), then ru, en, ja — same meaning, glossary terms,
   correct plural forms (ru: one/few/many/other; ja: other).
4. Check length: if a ru/ja string is much longer than uz in a button/tab, choose a shorter wording.
5. If keys belong to `billing`, `visa`, legal or refund texts, append them to `docs/i18n-review.md`
   for native-speaker review.
6. Run `make i18n-check` until it passes. Report in Uzbek: which keys were added, anything to review.
