"""One endpoint per provider. No user auth — the adapter verifies the provider's signature/credentials."""

from fastapi import APIRouter, Request, Response

from app.modules.billing.routers.deps import Registry, Session
from app.modules.billing.services import WebhookLedger

router = APIRouter(prefix="/webhooks", include_in_schema=False)


@router.post("/{provider}")
async def provider_webhook(provider: str, request: Request, session: Session, registry: Registry) -> Response:
    adapter = registry.get(provider)
    return await adapter.handle_webhook(request, WebhookLedger(session, adapter.name))
