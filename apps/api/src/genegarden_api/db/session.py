import asyncio
import logging
from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from genegarden_api.core.config import get_settings

_settings = get_settings()
_engine = create_async_engine(
    str(_settings.database_url),
    pool_pre_ping=True,
    echo=_settings.app_env == "development",
)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)
logger = logging.getLogger(__name__)


class DatabaseReadinessError(RuntimeError):
    """Raised without connection details when the database cannot serve a query."""


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with _session_factory() as session:
        yield session


async def close_database() -> None:
    await _engine.dispose()


async def check_database_connection() -> None:
    """Run a bounded round trip without exposing the database URL or driver error text."""

    try:
        async with asyncio.timeout(_settings.database_readiness_timeout_seconds):
            async with _engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError, TimeoutError) as exc:
        logger.warning("database_readiness_failed error_type=%s", type(exc).__name__)
        raise DatabaseReadinessError("Database is unavailable") from exc
