# 0006. Hosting on a VPS abroad behind Caddy

- Status: accepted
- Date: 2026-10-02

## Context
Users are in Uzbekistan and Japan. Solo developer, small budget, Docker Compose already used locally.
Uzbekistan's personal-data law requires personal data of Uzbek citizens to be stored on servers located in
Uzbekistan (localization requirement).

## Options
1. **VPS in Uzbekistan + CDN** — compliant with localization; fewer provider choices, higher price.
2. **VPS abroad (e.g. Hetzner)** — cheap, reliable, simple. Cons: conflicts with the localization requirement.
3. Decide later.

Reverse proxy: **Caddy** (automatic HTTPS, tiny config), Nginx (manual certificates), Traefik (more complex).

## Decision
The owner chose a VPS abroad (e.g. Hetzner) with Caddy as the reverse proxy, consciously accepting the
localization risk at this stage.

## Consequences
- Deploy = Docker Compose on the VPS + Caddy; deploy scripts in `infra/`.
- **Risk accepted:** non-compliance with personal-data localization. Mitigation: get legal advice before
  public launch; keep the app portable (no provider-specific managed services, plain Postgres/Redis/S3) so
  the database can move to an Uzbek data centre without code changes.
- Revisit before public launch or at the first sign of regulatory attention.
