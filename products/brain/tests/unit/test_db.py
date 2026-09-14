import asyncio
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from pydantic import PostgresDsn
from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
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
    async_session_scope,
    create_async_engine,
    create_async_session_factory,
    create_offline_engine,
    create_offline_session_factory,
    offline_session_scope,
)


async def test_engine_uses_typed_database_setting() -> None:
    engine = create_async_engine(
        Settings(
            database_url=PostgresDsn("postgresql+psycopg://user:password@database.example/brain")
        )
    )

    assert isinstance(engine, AsyncEngine)
    assert engine.url.drivername == "postgresql+psycopg"
    await engine.dispose()


async def test_session_scope_commits_and_closes() -> None:
    session = AsyncMock(spec=AsyncSession)

    async with async_session_scope(lambda: session) as yielded:
        assert yielded is session

    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()
    session.close.assert_called_once_with()


async def test_session_scope_rolls_back_and_closes() -> None:
    session = AsyncMock(spec=AsyncSession)

    with pytest.raises(RuntimeError, match="failed"):
        async with async_session_scope(lambda: session):
            raise RuntimeError("failed")

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
    session.close.assert_called_once_with()


async def test_session_scope_isolates_concurrent_tasks() -> None:
    sessions = [AsyncMock(spec=AsyncSession), AsyncMock(spec=AsyncSession)]
    claimed: list[AsyncSession] = []

    def factory() -> AsyncSession:
        session = sessions[len(claimed)]
        claimed.append(session)
        return session

    entered = asyncio.Event()
    active: set[int] = set()

    async def operation() -> AsyncSession:
        async with async_session_scope(factory) as session:
            active.add(id(session))
            if len(active) == 2:
                entered.set()
            await asyncio.wait_for(entered.wait(), timeout=1)
            return session

    results = await asyncio.gather(operation(), operation())

    assert results == sessions
    assert results[0] is not results[1]
    for session in sessions:
        session.commit.assert_awaited_once_with()
        session.close.assert_awaited_once_with()


def test_offline_session_utility_is_explicit_and_transactional() -> None:
    session = Mock(spec=Session)

    with offline_session_scope(Mock(return_value=session)) as yielded:
        assert yielded is session

    session.commit.assert_called_once_with()
    session.close.assert_called_once_with()


def test_offline_session_utility_rolls_back_failures() -> None:
    session = Mock(spec=Session)

    with (
        pytest.raises(RuntimeError, match="failed"),
        offline_session_scope(Mock(return_value=session)),
    ):
        raise RuntimeError("failed")

    session.rollback.assert_called_once_with()
    session.close.assert_called_once_with()


def test_offline_factory_uses_a_synchronous_engine() -> None:
    engine = create_offline_engine(Settings())
    factory = create_offline_session_factory(engine)

    assert isinstance(engine, Engine)
    assert factory.kw["bind"] is engine
    engine.dispose()


async def test_session_factory_is_bound_to_engine() -> None:
    engine = create_async_engine(Settings())

    factory = create_async_session_factory(engine)

    assert factory.kw["bind"] is engine
    await engine.dispose()


def test_repository_participates_in_a_caller_owned_session() -> None:
    session = AsyncMock(spec=AsyncSession)

    repository = Repository(session)

    assert repository.session is session


async def test_knowledge_repository_queries_and_adds_with_caller_session() -> None:
    session = AsyncMock(spec=AsyncSession)
    repository = KnowledgeRepository(session)
    organization_id = uuid4()
    record_id = uuid4()
    group_id = uuid4()

    session.scalar.return_value = None
    assert await repository.policy_group_ids(organization_id, record_id) is None
    assert await repository.principal_exists(organization_id, record_id) is False
    assert await repository.context_is_valid(organization_id, record_id, frozenset()) is False

    session.scalar.return_value = record_id
    session.scalars.return_value = [group_id]
    assert await repository.policy_group_ids(organization_id, record_id) == {group_id}
    assert await repository.principal_exists(organization_id, record_id) is True
    assert await repository.context_is_valid(organization_id, record_id, frozenset()) is True
    assert (
        await repository.context_is_valid(organization_id, record_id, frozenset({group_id})) is True
    )

    folder = Folder()
    source = Source()
    page = Page()
    for record, getter in (
        (folder, repository.get_folder),
        (source, repository.get_source),
        (page, repository.get_page),
    ):
        session.scalar.return_value = record
        assert await getter(organization_id, record_id) is record
    session.scalar.return_value = page
    assert await repository.get_page(organization_id, record_id, lock=True) is page

    await repository.add_folder(folder)
    await repository.add_source(source)
    await repository.add_page(page)
    version = PageVersion(page_id=record_id, version=1)
    await repository.add_version(version)
    link = PageVersionSource()
    await repository.add_version_source(link)
    assert session.add.call_count == 5

    session.scalars.return_value = [version]
    assert await repository.versions(record_id) == [version]
    session.scalar.return_value = None
    assert await repository.next_version(record_id) == 1
    result = Mock()
    result.tuples.return_value = [(link, source)]
    session.execute.return_value = result
    assert await repository.provenance(record_id) == [(link, source)]
