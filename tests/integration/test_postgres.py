import os

import psycopg
import pytest


@pytest.mark.integration
def test_postgres_has_vector_extension() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")

    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        row = cursor.fetchone()

    assert row is not None
