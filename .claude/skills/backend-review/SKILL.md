---
name: backend-review
description: Run the full backend review for a module or the current diff — architecture boundaries, security and database performance in parallel — and fix the findings. Use before releasing a backend module or merging a large backend change.
argument-hint: [module name, or empty for current diff]
---

Review backend: $ARGUMENTS

1. Determine scope: the named module under `backend/app/modules/`, or the files changed vs `main`.
2. In parallel, launch subagents `architect`, `security-auditor` and `db-performance` on that scope.
3. Merge their findings into one list, deduplicated, ordered: Critical/High security → boundary violations
   → performance wins → the rest.
4. Fix Critical/High and boundary issues; for each performance item, apply it if it's local and safe,
   otherwise list it as a follow-up.
5. Run from `backend/`: `uv run pytest && uv run lint-imports && uv run mypy app`.
6. Report in Uzbek: what was found, what was fixed, what's left.
