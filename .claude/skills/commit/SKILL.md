---
name: commit
description: Create a Conventional Commit for the current changes after running the quality gate. Use when the user asks to commit.
disable-model-invocation: true
---

1. Run the `/check` steps for touched apps; don't commit if anything is red.
2. Review `git diff`. If the changes are unrelated to each other, split them into several commits.
3. Message format: `type(scope): summary` — type ∈ feat, fix, refactor, test, docs, chore, perf;
   scope = `backend/<module>`, `frontend/<slice>`, `bot`, `infra`. Imperative, ≤ 72 chars, English.
   Body: why, not what.
4. `git add` only the relevant files (never `.env`), then commit. Do not push.
