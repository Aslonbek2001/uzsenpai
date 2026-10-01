"""auth — how people sign in: identities (Telegram, email + password, Google), sessions (refresh tokens).

Owns: auth_identities, auth_sessions (FK to users_users allowed by ADR 0008). Other modules import only `public`.
"""
