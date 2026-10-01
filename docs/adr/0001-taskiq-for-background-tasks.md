# 0001. Taskiq for background tasks

- Status: accepted
- Date: 2026-10-02

## Context
The backend needs background work: PDF rendering (resume), RAG ingestion and embeddings, AI batch jobs,
visa-expiry reminders, and processing the durable-event outbox with retries. Constraints: async FastAPI
codebase, solo developer, Redis is the only broker allowed (docs/STACK.md §5).

## Options
1. **arq** — tiny, async, Redis-only, was the initial assumption. Cons: maintenance-only, no new features.
2. **Taskiq + taskiq-redis** — async-native, actively developed, FastAPI integration (shared dependencies),
   scheduler for periodic tasks. Cons: slightly larger surface than arq.
3. **Celery** — most widely used. Cons: sync-first, heavier to run and configure; overkill for one developer.

## Decision
Taskiq with the Redis broker (`taskiq`, `taskiq-redis`). It fits the async codebase, keeps Redis as the only
broker, and is actively maintained, which matters for a long-lived product.

## Consequences
- `worker` service in compose runs the Taskiq worker; periodic jobs (reminders, outbox sweep) use the
  Taskiq scheduler.
- Module background work lives in `modules/<name>/jobs/` as Taskiq tasks, triggered via the outbox.
- Docs updated: STACK.md, CLAUDE.md, backend/CLAUDE.md, `modular-monolith` skill, `db-performance` agent.
- Revisit if Taskiq stops being maintained; tasks stay thin wrappers over services, so swapping is cheap.
