---
name: check
description: Run the full quality gate (lint, types, module boundaries, tests) for the apps touched by current changes and fix what fails. Use before committing or when the user says "tekshir" / "check".
---

1. `git status --short` → find which of backend/, frontend/, bot/ changed.
2. For each changed app run its lint, typecheck and tests (commands in that app's CLAUDE.md).
   Backend always also runs `uv run lint-imports`. Always run `make i18n-check` (uz, ru, en, ja).
3. Fix failures caused by the current changes. If a failure is pre-existing and unrelated, report it, don't fix it.
4. Re-run until green. Report in Uzbek: what ran, what you fixed, anything left.
