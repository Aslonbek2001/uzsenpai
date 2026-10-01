"""app/main.py — composition root: wires modules together. No business logic here."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import health
from app.core.config import settings
from app.core.db import engine
from app.core.logging import configure_logging
from app.core.redis import redis
from app.core.tasks import broker
from app.shared.errors import install_error_handlers

# One line per module router. Event subscriptions also live here, e.g.:
# from app.modules.notifications.handlers import register as register_notifications
# register_notifications(bus)
MODULE_ROUTERS: list[APIRouter] = []


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    if not broker.is_worker_process:
        await broker.startup()  # the API only enqueues tasks; the worker process runs them
    yield
    if not broker.is_worker_process:
        await broker.shutdown()
    await redis.aclose()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="UzSenpai API",
        version="1.0.0",
        lifespan=lifespan,
        # Interactive docs only outside production; the OpenAPI schema stays available for `make api-types`.
        docs_url=None if settings.env == "production" else "/docs",
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)
    app.include_router(health.router)
    for router in MODULE_ROUTERS:
        app.include_router(router)
    return app


app = create_app()
