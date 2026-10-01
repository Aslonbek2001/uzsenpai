# 0007. Google sign-in and PyJWT

- Status: accepted
- Date: 2026-10-02

## Context
Sign-in methods at launch: Telegram, email + password, and (owner's choice) Google. Access tokens are JWTs
(docs/STACK.md, Auth), but no JWT library was named. Google sign-in needs ID-token verification against
Google's public keys.

## Options
1. **PyJWT** (with `cryptography` for RS256) — small, widely used; verifies Google ID tokens via its JWKS client
   and signs our own access tokens. OAuth code exchange done with `httpx` (already in the stack).
2. **Authlib** — full OAuth client + JOSE. Cons: much larger surface than we need.
3. **google-auth** — Google's own library. Cons: Google-only; we would still need a JWT library for our tokens.

## Decision
PyJWT for both our access tokens and Google ID-token verification; the Google OAuth authorization-code flow
(with PKCE) is implemented with `httpx`. Identities store Google's stable `sub`, never the email as the key.

## Consequences
- Dependencies: `pyjwt[crypto]` (added when the auth endpoints are built).
- Settings: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `JWT_SECRET` (env only).
- Revisit if more OAuth providers (Apple, LINE) are added — Authlib may then pay off.
