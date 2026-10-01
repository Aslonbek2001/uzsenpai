"""app/main.py — composition root: wires modules together. No business logic here."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import outbox as _outbox  # noqa: F401  (registers core_outbox with Base.metadata)
from app.core.config import settings
from app.modules.billing.public import build_provider_registry
from app.modules.billing.routers import router as billing_router
from app.modules.catalog.routers import router as catalog_router
from app.modules.visa.routers import router as visa_router
from app.shared.errors import install_error_handlers

# One line per module. Event subscriptions also live here, e.g.:
# from app.modules.notifications.handlers import register as register_notifications
# register_notifications(bus)
MODULE_ROUTERS = [visa_router, catalog_router, billing_router]


def create_app() -> FastAPI:
    app = FastAPI(title="UzSenpai API", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)
    app.state.payment_providers = build_provider_registry(settings)
    app.state.checkout_return_url = f"{settings.public_web_url}/checkout/return"
    for router in MODULE_ROUTERS:
        app.include_router(router)
    return app


app = create_app()
