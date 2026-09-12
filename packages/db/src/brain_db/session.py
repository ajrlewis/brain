from collections.abc import Generator
from contextlib import contextmanager
from typing import Protocol

from sqlalchemy import Engine
from sqlalchemy import create_engine as sqlalchemy_create_engine
from sqlalchemy.orm import Session, sessionmaker


class SessionFactory(Protocol):
    """Injectable boundary used by repositories and application services."""

    def __call__(self) -> Session: ...


class DatabaseSettings(Protocol):
    @property
    def database_url(self) -> object: ...


def create_engine(settings: DatabaseSettings) -> Engine:
    return sqlalchemy_create_engine(str(settings.database_url), pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


@contextmanager
def session_scope(factory: SessionFactory) -> Generator[Session]:
    """Commit a unit of work, rolling it back if the operation fails."""

    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
