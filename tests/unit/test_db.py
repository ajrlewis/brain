from unittest.mock import Mock

import pytest
from pydantic import PostgresDsn
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from brain_core import Settings
from brain_db import Repository, create_engine, create_session_factory, session_scope


def test_engine_uses_typed_database_setting() -> None:
    engine = create_engine(
        Settings(
            database_url=PostgresDsn("postgresql+psycopg://user:password@database.example/brain")
        )
    )

    assert isinstance(engine, Engine)
    assert engine.url.drivername == "postgresql+psycopg"
    engine.dispose()


def test_session_scope_commits_and_closes() -> None:
    session = Mock(spec=Session)

    with session_scope(lambda: session) as yielded:
        assert yielded is session

    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()
    session.close.assert_called_once_with()


def test_session_scope_rolls_back_and_closes() -> None:
    session = Mock(spec=Session)

    with pytest.raises(RuntimeError, match="failed"), session_scope(lambda: session):
        raise RuntimeError("failed")

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
    session.close.assert_called_once_with()


def test_session_factory_is_bound_to_engine() -> None:
    engine = create_engine(Settings())

    factory = create_session_factory(engine)

    assert factory.kw["bind"] is engine
    engine.dispose()


def test_repository_participates_in_a_caller_owned_session() -> None:
    session = Mock(spec=Session)

    repository = Repository(session)

    assert repository.session is session
