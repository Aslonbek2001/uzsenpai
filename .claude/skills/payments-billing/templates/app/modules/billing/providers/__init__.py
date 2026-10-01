"""Payment provider adapters. Each provider is its own package; all implement `base.PaymentProvider`.

National (UZS): click, payme, uzum.   International (USD/JPY/EUR): chosen by ADR, plugs in the same way.
`fake` is a full in-memory provider for local dev and tests — never enabled in production.
"""
