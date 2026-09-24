import re
import traceback
from typing import Self

import pytest
from sqlalchemy.engine import make_url

from tests.conftest import (
    DEFAULT_TEST_DATABASE_URL,
    DatabaseCreationError,
    DatabaseTargetError,
    TestDatabaseConfig,
    create_test_database,
    generate_database_name,
    validate_lifecycle_target,
)

MAINTENANCE_PASSWORD_CANARY_PARTS = ("r1", "harness", "canary", "value")
MAINTENANCE_PASSWORD_CANARY = "-".join(MAINTENANCE_PASSWORD_CANARY_PARTS)


def _unreachable_maintenance_config() -> TestDatabaseConfig:
    url = f"postgresql+psycopg://owner:{MAINTENANCE_PASSWORD_CANARY}@127.0.0.1:1/r1_test"
    return TestDatabaseConfig(template_url=make_url(url))


class FakeMaintenanceCursor:
    def __init__(self, oid_results: list[tuple[int] | None]) -> None:
        self.oid_results = oid_results
        self.statements: list[str] = []
        self.current = ""

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, query: object, params: object = None) -> None:
        self.current = str(query)
        self.statements.append(self.current)

    def fetchone(self) -> tuple[int] | None:
        if "hashtextextended" in self.current:
            return (123456,)
        if "FROM pg_database" in self.current:
            return self.oid_results.pop(0)
        return None


class FakeMaintenanceConnection:
    def __init__(self, oid_results: list[tuple[int] | None]) -> None:
        self.closed = False
        self.test_cursor = FakeMaintenanceCursor(oid_results)

    def cursor(self) -> FakeMaintenanceCursor:
        return self.test_cursor

    def close(self) -> None:
        self.closed = True


def test_database_config_uses_the_documented_compose_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)

    config = TestDatabaseConfig.from_environment()

    assert config.template_url.render_as_string(hide_password=False) == DEFAULT_TEST_DATABASE_URL
    assert config.maintenance_url.database == "postgres"


def test_database_config_reads_only_test_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    explicit = "postgresql+psycopg://owner:secret@db.example:5544/arbitrary_template"
    monkeypatch.setenv("TEST_DATABASE_URL", explicit)
    monkeypatch.setenv("DATABASE_URL", "not-a-database-url")

    config = TestDatabaseConfig.from_environment()

    assert config.template_url.render_as_string(hide_password=False) == explicit
    assert config.maintenance_url.host == "db.example"
    assert config.maintenance_url.port == 5544
    assert config.maintenance_url.database == "postgres"


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql://postgres:postgres@127.0.0.1:5432/template",
        "postgresql+psycopg://:postgres@127.0.0.1:5432/template",
        "postgresql+psycopg://postgres@127.0.0.1:5432/template",
        "postgresql+psycopg://postgres:postgres@:5432/template",
        "postgresql+psycopg://postgres:postgres@host-a,host-b:5432/template",
        "postgresql+psycopg://postgres:postgres@127.0.0.1/template",
        "postgresql+psycopg://postgres:postgres@127.0.0.1:not-a-port/template",
        "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/template?sslmode=disable",
        "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/template#fragment",
        "postgresql+psycopg://postgres:postgres@/template?host=/var/run/postgresql",
    ],
)
def test_database_config_rejects_ambiguous_or_unsafe_urls_before_sql(
    monkeypatch: pytest.MonkeyPatch,
    database_url: str,
) -> None:
    connect_calls: list[str] = []

    def forbidden_connect(*args: object, **kwargs: object) -> None:
        connect_calls.append("called")
        raise AssertionError("validation must finish before any SQL connection")

    monkeypatch.setenv("TEST_DATABASE_URL", database_url)
    monkeypatch.setattr("psycopg.connect", forbidden_connect)

    with pytest.raises(ValueError, match="TEST_DATABASE_URL"):
        TestDatabaseConfig.from_environment()

    assert connect_calls == []


def test_invalid_database_url_diagnostic_does_not_retain_the_raw_dsn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "p106-dsn-canary-value"
    monkeypatch.setenv(
        "TEST_DATABASE_URL",
        f"postgresql+psycopg://owner:{secret}@127.0.0.1:not-a-port/template",
    )

    with pytest.raises(ValueError) as raised:
        TestDatabaseConfig.from_environment()

    error = raised.value
    assert error.__cause__ is None
    assert error.__context__ is None
    assert secret not in str(error)
    assert secret not in repr(error)
    assert secret not in "".join(traceback.format_exception(error))


def test_generated_database_names_are_unique_and_exactly_guarded() -> None:
    names = {generate_database_name() for _ in range(20)}

    assert len(names) == 20
    assert all(len(name) == 41 for name in names)
    assert all(re.fullmatch(r"bmp_test_[0-9a-f]{32}", name) for name in names)


@pytest.mark.parametrize(
    "name",
    [
        "postgres",
        "template0",
        "template1",
        "business_management_platform",
        "business_management_platform_test",
        "bmp_test",
        "bmp_test_ABCDEF0123456789abcdef0123456789",
        "bmp_test_abcdef0123456789abcdef0123456789_extra",
    ],
)
def test_lifecycle_target_guard_rejects_reserved_or_malformed_names(name: str) -> None:
    with pytest.raises(DatabaseTargetError):
        validate_lifecycle_target(name, application_database_names={"custom_application"})


def test_lifecycle_target_guard_rejects_the_configured_application_database() -> None:
    name = "bmp_test_0123456789abcdef0123456789abcdef"

    with pytest.raises(DatabaseTargetError):
        validate_lifecycle_target(name, application_database_names={name})


def test_target_guard_failure_occurs_without_opening_a_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connect_calls: list[str] = []

    def forbidden_connect(*args: object, **kwargs: object) -> None:
        connect_calls.append("called")
        raise AssertionError("target validation must finish before connecting")

    monkeypatch.setattr("psycopg.connect", forbidden_connect)

    with pytest.raises(DatabaseTargetError):
        validate_lifecycle_target("postgres", application_database_names=set())

    assert connect_calls == []


def test_preexisting_generated_name_is_never_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    name = "bmp_test_0123456789abcdef0123456789abcdef"
    connection = FakeMaintenanceConnection([(9876,)])
    config = TestDatabaseConfig(template_url=make_url(DEFAULT_TEST_DATABASE_URL))
    monkeypatch.setattr("tests.conftest.generate_database_name", lambda: name)
    monkeypatch.setattr("psycopg.connect", lambda *args, **kwargs: connection)

    with (
        pytest.raises(DatabaseCreationError, match="already exists"),
        create_test_database(config),
    ):
        raise AssertionError("the collision must stop before workload setup")

    statements = "\n".join(connection.test_cursor.statements)
    assert "CREATE DATABASE" not in statements
    assert "DROP DATABASE" not in statements
    assert connection.closed


def test_ambiguous_create_outcome_is_not_guessed_or_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    name = "bmp_test_fedcba9876543210fedcba9876543210"
    connection = FakeMaintenanceConnection([None, None])
    config = TestDatabaseConfig(template_url=make_url(DEFAULT_TEST_DATABASE_URL))
    monkeypatch.setattr("tests.conftest.generate_database_name", lambda: name)
    monkeypatch.setattr("psycopg.connect", lambda *args, **kwargs: connection)

    with pytest.raises(DatabaseCreationError, match="ambiguous"), create_test_database(config):
        raise AssertionError("ambiguous ownership must not reach workload setup")

    statements = "\n".join(connection.test_cursor.statements)
    assert "CREATE DATABASE" in statements
    assert "DROP DATABASE" not in statements
    assert connection.closed


@pytest.mark.unit
def test_maintenance_connection_failure_redacts_database_password() -> None:
    config = _unreachable_maintenance_config()

    with pytest.raises(DatabaseCreationError) as raised, create_test_database(config):
        pytest.fail("port 1 must not reach the workload")

    assert str(raised.value) == "could not connect to the maintenance database"
    assert MAINTENANCE_PASSWORD_CANARY not in str(raised.getrepr())
    assert MAINTENANCE_PASSWORD_CANARY not in str(
        raised.getrepr(style="long", showlocals=True, funcargs=True, chain=True)
    )
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
