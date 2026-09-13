from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Protocol

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.ext.asyncio import (
    create_async_engine as sqlalchemy_create_async_engine,
)


class AsyncSessionFactory(Protocol):
    """Injectable runtime boundary used by repositories and application services."""

    def __call__(self) -> AsyncSession: ...


class DatabaseSettings(Protocol):
    @property
    def database_url(self) -> object: ...

    @property
    def database_pool_size(self) -> int: ...

    @property
    def database_max_overflow(self) -> int: ...

    @property
    def database_pool_timeout_seconds(self) -> float: ...

    @property
    def database_pool_recycle_seconds(self) -> int: ...

    @property
    def database_statement_timeout_ms(self) -> int: ...

    @property
    def database_lock_timeout_ms(self) -> int: ...


def create_async_engine(settings: DatabaseSettings) -> AsyncEngine:
    options = (
        f"-c statement_timeout={settings.database_statement_timeout_ms} "
        f"-c lock_timeout={settings.database_lock_timeout_ms}"
    )
    return sqlalchemy_create_async_engine(
        str(settings.database_url),
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
    """Own one runtime unit of work and always commit/rollback and close it."""

    session = factory()
    try:
        yield session
        await session.commit()
    except BaseException:
        await session.rollback()
        raise
    finally:
        await session.close()
