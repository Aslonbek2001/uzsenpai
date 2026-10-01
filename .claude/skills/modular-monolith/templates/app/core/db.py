"""app/core/db.py — engine, Base, one session (= one transaction) per request."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.events import bus

engine = create_async_engine(settings.database_url, pool_size=10, max_overflow=10, pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncIterator[AsyncSession]:
    """One session = one transaction per request. Commits once at the end; events run only after commit.

    Always use it through `SessionDep` (scope="function"): FastAPI then finishes this dependency — including the
    COMMIT — BEFORE the response is sent. With the default request scope the client (e.g. a payment provider)
    would receive 200 before the commit, and a failed commit would silently lose a paid order.
    """
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            bus.discard(session)
            raise
        await bus.dispatch_committed(session)


SessionDep = Annotated[AsyncSession, Depends(get_session, scope="function")]
