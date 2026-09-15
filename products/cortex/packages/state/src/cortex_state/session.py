from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine as sqlalchemy_create_async_engine


class AsyncSessionFactory(Protocol):
    def __call__(self) -> AsyncSession: ...


class DatabaseSettings(Protocol):
    cortex_database_url: object
    database_pool_size: int
    database_max_overflow: int
    database_pool_timeout_seconds: float
    database_pool_recycle_seconds: int
    database_statement_timeout_ms: int
    database_lock_timeout_ms: int


def create_async_engine(settings: DatabaseSettings) -> AsyncEngine:
    options = (
        f"-c statement_timeout={settings.database_statement_timeout_ms} "
        f"-c lock_timeout={settings.database_lock_timeout_ms}"
    )
    return sqlalchemy_create_async_engine(
        str(settings.cortex_database_url),
        pool_pre_ping=True,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout_seconds,
        pool_recycle=settings.database_pool_recycle_seconds,
        connect_args={"options": options},
    )


def create_async_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, expire_on_commit=False)


@asynccontextmanager
async def async_session_scope(factory: AsyncSessionFactory) -> AsyncGenerator[AsyncSession]:
    session = factory()
    try:
        yield session
        await session.commit()
    except BaseException:
        await session.rollback()
        raise
    finally:
        await session.close()
