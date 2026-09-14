"""Synchronous database utilities for migrations and explicit seed commands only."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Protocol

from sqlalchemy import Engine
from sqlalchemy import create_engine as sqlalchemy_create_engine
from sqlalchemy.orm import Session, sessionmaker


class OfflineDatabaseSettings(Protocol):
    @property
    def database_url(self) -> object: ...


def create_offline_engine(settings: OfflineDatabaseSettings) -> Engine:
    return sqlalchemy_create_engine(str(settings.database_url), pool_pre_ping=True)


def create_offline_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


@contextmanager
def offline_session_scope(factory: sessionmaker[Session]) -> Generator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()
