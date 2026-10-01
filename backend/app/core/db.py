"""app/core/db.py — engine, Base, one session (= one transaction) per request."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import StrEnum
from typing import Annotated

from fastapi import Depends
from sqlalchemy import CheckConstraint, Enum, MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.events import bus

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,
)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)

# Deterministic constraint names, so Alembic autogenerate can create and drop them reliably.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def str_enum(enum_cls: type[StrEnum], *, length: int = 20) -> Enum:
    """Column type for a StrEnum: VARCHAR storing `.value` (adding a value later = a small migration).
    Pair it with `enum_check(...)` in `__table_args__`."""
    return Enum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda members: [m.value for m in members],
    )


def enum_check(column: str, enum_cls: type[StrEnum]) -> CheckConstraint:
    """CHECK (<column> IN (...)) named by the convention: ck_<table>_<column>."""
    values = ", ".join(f"'{m.value}'" for m in enum_cls)
    return CheckConstraint(f"{column} IN ({values})", name=column)


@asynccontextmanager
async def unit_of_work() -> AsyncIterator[AsyncSession]:
    """One transaction outside a request (Taskiq jobs, scripts): commit at the end, then run after-commit events
    (incl. kicking new outbox rows). Rolls back and drops queued events on error."""
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            bus.discard(session)
            raise
        await bus.dispatch_committed(session)


async def get_session() -> AsyncIterator[AsyncSession]:
    """One session = one transaction per request. Commits once at the end; events run only after commit.

    Always use it through `SessionDep` (scope="function"): FastAPI then finishes this dependency — including the
    COMMIT — BEFORE the response is sent. With the default request scope the client (e.g. a payment provider)
    would receive 200 before the commit, and a failed commit would silently lose a paid order.
    """
    async with unit_of_work() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session, scope="function")]
