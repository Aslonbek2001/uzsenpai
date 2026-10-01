"""Alembic environment — one shared migration history for all modules (async engine)."""

import asyncio
import importlib
import pkgutil
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

import app.core.outbox  # core tables (the outbox) for autogenerate
import app.modules
from app.core.config import settings
from app.core.db import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def import_all_models() -> None:
    """Import `app.modules.<name>.models` for every module, so autogenerate sees every table."""
    for info in pkgutil.iter_modules(app.modules.__path__):
        try:
            importlib.import_module(f"app.modules.{info.name}.models")
        except ModuleNotFoundError as exc:
            if exc.name != f"app.modules.{info.name}.models":
                raise  # a real import error inside models, not "module has no models"


import_all_models()
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(settings.database_url, poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
