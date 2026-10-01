# 0008. Foreign key from auth to users

- Status: accepted
- Date: 2026-10-02

## Context
Modules must not hold foreign keys into other modules' tables (.claude/rules/database.md) so they stay
independent. `auth` (identities, sessions) and `users` (the person) are always deployed together, and an
identity or session without its user is a security bug (a login that resolves to nobody).

## Options
1. **FK `auth_* .user_id → users_users.id` (ON DELETE CASCADE)** — the database guarantees no orphan logins.
2. **Store the id only** — follows the rule; orphans prevented only by code.

## Decision
Allow foreign keys from `auth_identities` and `auth_sessions` to `users_users`. The exception covers this
pair only; every other cross-module reference still stores the id without an FK.

## Consequences
- Migrations must create `users_users` before `auth_*` tables (one shared Alembic history already does).
- `auth` code still never imports `users` models — the FK is declared by table name; data access goes through
  `users.public`.
- Users are anonymized rather than hard-deleted, so CASCADE fires only for test cleanup or a manual purge.
