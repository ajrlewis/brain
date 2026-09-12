from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import PostgresDsn
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from brain_core import Settings
from brain_db import (
    Folder,
    KnowledgeRepository,
    Page,
    PageVersion,
    PageVersionSource,
    Repository,
    Source,
    create_engine,
    create_session_factory,
    session_scope,
)


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


def test_knowledge_repository_queries_and_adds_with_caller_session() -> None:
    session = Mock(spec=Session)
    repository = KnowledgeRepository(session)
    organization_id = uuid4()
    record_id = uuid4()
    group_id = uuid4()

    session.scalar.return_value = None
    assert repository.policy_group_ids(organization_id, record_id) is None
    assert repository.principal_exists(organization_id, record_id) is False
    assert repository.context_is_valid(organization_id, record_id, frozenset()) is False

    session.scalar.return_value = record_id
    session.scalars.return_value = [group_id]
    assert repository.policy_group_ids(organization_id, record_id) == {group_id}
    assert repository.principal_exists(organization_id, record_id) is True
    assert repository.context_is_valid(organization_id, record_id, frozenset()) is True
    assert repository.context_is_valid(organization_id, record_id, frozenset({group_id})) is True

    folder = Folder()
    source = Source()
    page = Page()
    for record, getter in (
        (folder, repository.get_folder),
        (source, repository.get_source),
        (page, repository.get_page),
    ):
        session.scalar.return_value = record
        assert getter(organization_id, record_id) is record
    session.scalar.return_value = page
    assert repository.get_page(organization_id, record_id, lock=True) is page

    repository.add_folder(folder)
    repository.add_source(source)
    repository.add_page(page)
    version = PageVersion(page_id=record_id, version=1)
    repository.add_version(version)
    link = PageVersionSource()
    repository.add_version_source(link)
    assert session.add.call_count == 5

    session.scalars.return_value = [version]
    assert repository.versions(record_id) == [version]
    session.scalar.return_value = None
    assert repository.next_version(record_id) == 1
    session.execute.return_value.tuples.return_value = [(link, source)]
    assert repository.provenance(record_id) == [(link, source)]
