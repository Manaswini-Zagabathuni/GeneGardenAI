from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from genegarden_api.core.config import get_settings

_settings = get_settings()
_engine = create_async_engine(
    str(_settings.database_url),
    pool_pre_ping=True,
    echo=_settings.app_env == "development",
)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with _session_factory() as session:
        yield session


async def close_database() -> None:
    await _engine.dispose()
