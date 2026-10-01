# ruff: noqa: E402 — env vars must be set before the app (and its settings) are imported
"""backend/conftest.py — shared fixtures for ALL tests (backend/tests and app/modules/*/tests).

Provides: app, client, per-test DB transaction, fake auth.

Every test runs inside one outer transaction that is rolled back at the end; the app's own commits become
SAVEPOINT releases, so tests never leak data into each other. Point TEST_DATABASE_URL at the compose
Postgres test database (`uzsenpai_test`). PostgreSQL only — SQLite's SAVEPOINT handling breaks this isolation.
"""

import os
import uuid
from collections.abc import AsyncIterator

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://uzsenpai:uzsenpai@localhost:5432/uzsenpai_test"
)
# Before importing app: settings are read at import time. The app's own engine must point at the test DB too
# (tests that need real commits — concurrency, commit-before-ack — use it directly).
os.environ.setdefault("ENV", "test")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest
from fastapi import FastAPI, HTTPException, Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.core.db import Base, get_session
from app.core.db import engine as app_engine
from app.core.events import bus
from app.main import create_app
from app.modules.auth.public import CurrentUser, current_user

USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
OTHER_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


@pytest.fixture(scope="session")
async def engine():  # type: ignore[no-untyped-def]
    eng = create_async_engine(TEST_DATABASE_URL)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)  # real projects: run `alembic upgrade head` instead
    yield eng
    await eng.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncIterator[AsyncSession]:  # type: ignore[no-untyped-def]
    async with engine.connect() as conn:
        outer = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            await session.close()
            await outer.rollback()


async def _fake_current_user(request: Request) -> CurrentUser:
    """Tests authenticate with `Authorization: Bearer test-<uuid>`; no header → 401 like the real thing."""
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer test-"):
        raise HTTPException(status_code=401)
    return CurrentUser(id=uuid.UUID(auth.removeprefix("Bearer test-")))


@pytest.fixture
async def app(db_session: AsyncSession) -> AsyncIterator[FastAPI]:
    application = create_app()

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
    application.dependency_overrides[current_user] = _fake_current_user
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer test-{USER_ID}"}


@pytest.fixture
def other_user_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer test-{OTHER_USER_ID}"}


@pytest.fixture
async def committing_app(engine: AsyncEngine) -> AsyncIterator[FastAPI]:
    """App with REAL commits (no savepoint override) for concurrency / commit-before-ack tests.
    Every table is emptied afterwards. Auth is faked the same way as in `app`."""
    await app_engine.dispose()
    application = create_app()
    application.dependency_overrides[current_user] = _fake_current_user
    yield application
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(delete(table))
    await app_engine.dispose()
