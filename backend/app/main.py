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
from app.modules.auth.routers import router as auth_router
from app.modules.users.routers import router as users_router
from app.shared.errors import install_error_handlers
from app.wiring import wire_events

# One line per module router. Event subscriptions live in app/wiring.py (shared with the worker).
MODULE_ROUTERS: list[APIRouter] = [auth_router, users_router]


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
    wire_events()
    install_error_handlers(app)
    app.include_router(health.router)
    for router in MODULE_ROUTERS:
        app.include_router(router)
    return app


app = create_app()
