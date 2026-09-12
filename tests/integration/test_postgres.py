import os
from uuid import uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg.errors import CheckViolation, ForeignKeyViolation


@pytest.mark.integration
def test_postgres_has_vector_extension() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")

    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        row = cursor.fetchone()

    assert row is not None


@pytest.mark.integration
def test_clean_database_migration_and_tenant_constraints(monkeypatch: pytest.MonkeyPatch) -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")

    sqlalchemy_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    monkeypatch.setenv("DATABASE_URL", sqlalchemy_url)
    config = Config("alembic.ini")
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    organization_a = uuid4()
    organization_b = uuid4()
    principal_a = uuid4()
    group_b = uuid4()
    policy_a = uuid4()
    with (
        psycopg.connect(database_url, autocommit=True) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("SELECT version_num FROM alembic_version")
        assert cursor.fetchone() == ("20260912_0001",)
        cursor.execute(
            "INSERT INTO organizations (id, slug, name) "
            "VALUES (%s, 'alpha', 'Alpha'), (%s, 'beta', 'Beta')",
            (organization_a, organization_b),
        )
        cursor.execute(
            "INSERT INTO principals "
            "(id, organization_id, kind, external_subject, display_name) "
            "VALUES (%s, %s, 'user', 'alpha-user', 'Alpha User')",
            (principal_a, organization_a),
        )
        cursor.execute(
            "INSERT INTO groups (id, organization_id, slug, name) "
            "VALUES (%s, %s, 'beta-group', 'Beta Group')",
            (group_b, organization_b),
        )
        cursor.execute(
            "INSERT INTO access_policies (id, organization_id, name) VALUES (%s, %s, %s)",
            (policy_a, organization_a, "Alpha policy"),
        )
        with pytest.raises(ForeignKeyViolation):
            cursor.execute(
                "INSERT INTO group_memberships "
                "(organization_id, group_id, principal_id) VALUES (%s, %s, %s)",
                (organization_a, group_b, principal_a),
            )
        with pytest.raises(ForeignKeyViolation):
            cursor.execute(
                "INSERT INTO access_policy_groups "
                "(organization_id, access_policy_id, group_id) VALUES (%s, %s, %s)",
                (organization_a, policy_a, group_b),
            )
        with pytest.raises(CheckViolation):
            cursor.execute(
                "INSERT INTO principals "
                "(organization_id, kind, external_subject, display_name) "
                "VALUES (%s, 'administrator', 'invalid', 'Invalid')",
                (organization_a,),
            )
        cursor.execute("TRUNCATE organizations CASCADE")
