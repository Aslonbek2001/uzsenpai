# ruff: noqa: E402 — env vars must be set before the app (and its settings) are imported
"""backend/conftest.py — shared fixtures for ALL tests (backend/tests and app/modules/*/tests).

Provides: engine (test DB built by the real Alembic migrations), per-test DB transaction, app, client.

Every test runs inside one outer transaction that is rolled back at the end; the app's own commits become
SAVEPOINT releases, so tests never leak data into each other. Point TEST_DATABASE_URL at the compose
Postgres test database (`uzsenpai_test`). PostgreSQL only — SQLite's SAVEPOINT handling breaks this isolation.
Auth: `user_id` + `auth_headers` give a real user and a real access token.
"""

import asyncio
import os
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://uzsenpai:uzsenpai@localhost:5432/uzsenpai_test"
)
# Before importing app: settings are read at import time. The app's own engine (and Alembic) must point at the
# test DB too.
os.environ["ENV"] = "test"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
# Redis DB 15 is reserved for tests and flushed before each test (rate limits, codes)
os.environ["REDIS_URL"] = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/15")
os.environ["BOT_SERVICE_TOKEN"] = "test-bot-service-token-0123456789abcdef"  # noqa: S105 — test-only value
os.environ["TELEGRAM_BOT_TOKEN"] = "123456:test-telegram-bot-token"  # noqa: S105 — test-only value
os.environ["REFRESH_COOKIE_SECURE"] = "false"  # the test client talks plain http

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.core.db import get_session
from app.core.events import bus
from app.core.redis import redis
from app.main import create_app
from app.modules.auth.testing import auth_headers_for
from app.modules.users.testing import create_user

BACKEND_DIR = Path(__file__).resolve().parent


@pytest.fixture(scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(TEST_DATABASE_URL)
    async with eng.begin() as conn:  # start from an empty schema every run
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    # env.py runs its own event loop, so it must run outside this one
    await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
    yield eng
    await eng.dispose()


@pytest.fixture(autouse=True)
async def _clean_redis() -> None:
    await redis.flushdb()


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with engine.connect() as conn:
        outer = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            await session.close()
            await outer.rollback()


@pytest.fixture
async def app(db_session: AsyncSession) -> AsyncIterator[FastAPI]:
    application = create_app()
    # Rows written here live in a rolled-back transaction the worker could never see: don't enqueue them.
    bus.on_outbox_committed = None

    async def _session() -> AsyncIterator[AsyncSession]:
        # Mirrors get_session: roll back on error (so tests see what production would keep), commit otherwise.
        try:
            yield db_session
        except Exception:
            await db_session.rollback()
            bus.discard(db_session)
            raise
        await db_session.commit()  # releases the SAVEPOINT; the outer transaction is rolled back later
        await bus.dispatch_committed(db_session)

    application.dependency_overrides[get_session] = _session
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def user_id(db_session: AsyncSession) -> uuid.UUID:
    return await create_user(db_session)


@pytest.fixture
def auth_headers(user_id: uuid.UUID) -> dict[str, str]:
    """A real access token for `user_id` (signed with the test JWT secret)."""
    return auth_headers_for(user_id)
