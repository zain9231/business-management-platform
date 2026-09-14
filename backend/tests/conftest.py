import os
import re
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import Session

from app.core import clock
from app.core.config import Settings
from app.main import create_app

FrozenTime = Callable[[datetime], AbstractContextManager[datetime]]

DEFAULT_TEST_DATABASE_URL = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/bmp_test"
DATABASE_NAME_PATTERN = re.compile(r"^bmp_test_[0-9a-f]{32}$")
RESERVED_DATABASE_NAMES = frozenset(
    {
        "postgres",
        "template0",
        "template1",
        "business_management_platform",
        "business_management_platform_test",
    }
)


class DatabaseTargetError(ValueError):
    """Raised before SQL when a lifecycle target is not demonstrably run-owned."""


class DatabaseCreationError(RuntimeError):
    """Raised when database creation has an ambiguous or unsafe outcome."""


class DatabaseCleanupError(RuntimeError):
    """Raised when safe exact-target cleanup cannot proceed."""


class TestDatabaseConfig(BaseModel):
    """Validated test-only PostgreSQL lifecycle input."""

    __test__ = False
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    template_url: URL

    @property
    def maintenance_url(self) -> URL:
        return self.template_url.set(database="postgres")

    @classmethod
    def from_environment(cls) -> "TestDatabaseConfig":
        raw_url = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
        if "?" in raw_url or "#" in raw_url:
            raise ValueError("TEST_DATABASE_URL must not contain query or fragment components")

        try:
            url = make_url(raw_url)
            port = url.port
        except (ArgumentError, ValueError):
            url = None
            port = None

        if url is None:
            raise ValueError("TEST_DATABASE_URL must be a valid SQLAlchemy URL")

        if url.drivername != "postgresql+psycopg":
            raise ValueError("TEST_DATABASE_URL must use the postgresql+psycopg driver")
        if not url.username:
            raise ValueError("TEST_DATABASE_URL must contain a nonempty username")
        if not url.password:
            raise ValueError("TEST_DATABASE_URL must contain a nonempty password")
        if not url.host or "," in url.host:
            raise ValueError("TEST_DATABASE_URL must contain exactly one nonempty host")
        if port is None or not 1 <= port <= 65535:
            raise ValueError("TEST_DATABASE_URL must contain a valid explicit port")
        if not url.database:
            raise ValueError("TEST_DATABASE_URL must contain a template database name")

        return cls(template_url=url)


def generate_database_name() -> str:
    return f"bmp_test_{uuid4().hex}"


def validate_lifecycle_target(
    name: str,
    *,
    application_database_names: set[str],
) -> None:
    if not DATABASE_NAME_PATTERN.fullmatch(name):
        raise DatabaseTargetError("database target is not an exact generated P1-06 name")
    if name in RESERVED_DATABASE_NAMES or name in application_database_names:
        raise DatabaseTargetError("database target is reserved or application-owned")


def _application_database_names(config: TestDatabaseConfig) -> set[str]:
    names = {config.template_url.database or ""}
    application_url = os.environ.get("DATABASE_URL")
    if application_url:
        try:
            application_name = make_url(application_url).database
        except (ArgumentError, ValueError):
            application_name = None
        if application_name:
            names.add(application_name)
    return names


def _connection_string(url: URL) -> str:
    return url.set(drivername="postgresql").render_as_string(hide_password=False)


@dataclass
class TestDatabaseHarness:
    """Exclusive ownership record for one run-generated PostgreSQL database."""

    __test__ = False

    config: TestDatabaseConfig
    name: str
    oid: int
    lock_key: int
    maintenance_connection: psycopg.Connection[Any]
    engine: Engine
    application_database_names: set[str]
    events: list[str] = field(default_factory=list)
    closed: bool = False

    @property
    def url(self) -> URL:
        return self.config.template_url.set(database=self.name)

    @property
    def connection_string(self) -> str:
        return _connection_string(self.url)

    def catalog_snapshot(self) -> dict[str, int]:
        with self.maintenance_connection.cursor() as cursor:
            cursor.execute("SELECT datname, oid FROM pg_database ORDER BY datname")
            return {str(name): int(oid) for name, oid in cursor.fetchall()}

    def _ownership_lock_is_held(self) -> bool:
        with self.maintenance_connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_locks
                    WHERE locktype = 'advisory'
                      AND pid = pg_backend_pid()
                      AND classid::bigint = ((%s::bigint >> 32) & 4294967295)
                      AND objid::bigint = (%s::bigint & 4294967295)
                      AND objsubid = 1
                      AND granted
                )
                """,
                (self.lock_key, self.lock_key),
            )
            row = cursor.fetchone()
        return bool(row and row[0])

    def assert_safe_to_drop(self) -> None:
        validate_lifecycle_target(
            self.name,
            application_database_names=self.application_database_names,
        )
        self.engine.dispose()

        catalog = self.catalog_snapshot()
        if catalog.get(self.name) != self.oid:
            raise DatabaseCleanupError("owned database name and OID no longer match")
        if not self._ownership_lock_is_held():
            raise DatabaseCleanupError("owned database advisory lock is not held")

        with self.maintenance_connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT pid, application_name
                FROM pg_stat_activity
                WHERE datid = %s
                ORDER BY pid
                """,
                (self.oid,),
            )
            active_connections = cursor.fetchall()
        if active_connections:
            clients = ", ".join(
                f"pid={pid} application_name={application_name or '<unset>'}"
                for pid, application_name in active_connections
            )
            raise DatabaseCleanupError(
                f"database {self.name} leaked: active connection prevents exact cleanup: {clients}"
            )

    def _release_lock_and_close(self) -> None:
        if self.maintenance_connection.closed:
            return
        if self._ownership_lock_is_held():
            with self.maintenance_connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", (self.lock_key,))
        self.maintenance_connection.close()

    def close(self) -> None:
        if self.closed:
            return

        try:
            self.assert_safe_to_drop()
            with self.maintenance_connection.cursor() as cursor:
                cursor.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(self.name)))
                cursor.execute("SELECT oid FROM pg_database WHERE datname = %s", (self.name,))
                if cursor.fetchone() is not None:
                    raise DatabaseCleanupError("owned database remained after DROP DATABASE")
                cursor.execute("SELECT pg_advisory_unlock(%s)", (self.lock_key,))
                unlocked = cursor.fetchone()
                if unlocked != (True,):
                    raise DatabaseCleanupError("owned database advisory lock was not released")
            self.events.append(f"target={self.name} action=database-dropped")
            self.closed = True
        except Exception:
            self.events.append(f"target={self.name} action=cleanup-refused-or-failed")
            self.closed = True
            raise
        finally:
            self._release_lock_and_close()


@contextmanager
def create_test_database(config: TestDatabaseConfig) -> Iterator[TestDatabaseHarness]:
    name = generate_database_name()
    application_names = _application_database_names(config)
    validate_lifecycle_target(name, application_database_names=application_names)

    maintenance_connection = psycopg.connect(
        _connection_string(config.maintenance_url),
        autocommit=True,
        application_name="p106-test-database-owner",
    )
    lock_key: int | None = None
    harness: TestDatabaseHarness | None = None
    events: list[str] = []
    try:
        with maintenance_connection.cursor() as cursor:
            cursor.execute("SELECT hashtextextended(%s, 0)", (name,))
            lock_row = cursor.fetchone()
            if lock_row is None:
                raise DatabaseCreationError("could not derive the ownership lock key")
            lock_key = int(lock_row[0])
            cursor.execute("SELECT pg_advisory_lock(%s)", (lock_key,))
            events.append(f"target={name} action=advisory-lock-acquired")

            cursor.execute("SELECT oid FROM pg_database WHERE datname = %s", (name,))
            if cursor.fetchone() is not None:
                raise DatabaseCreationError("generated database name already exists")
            events.append(f"target={name} action=absence-confirmed")

            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
            events.append(f"target={name} action=database-created")
            cursor.execute("SELECT oid FROM pg_database WHERE datname = %s", (name,))
            oid_row = cursor.fetchone()
            if oid_row is None:
                raise DatabaseCreationError("database creation outcome is ambiguous")
            oid = int(oid_row[0])
            events.append(f"target={name} action=oid-recorded oid={oid}")

        engine = create_engine(
            config.template_url.set(database=name),
            pool_pre_ping=True,
        )
        harness = TestDatabaseHarness(
            config=config,
            name=name,
            oid=oid,
            lock_key=lock_key,
            maintenance_connection=maintenance_connection,
            engine=engine,
            application_database_names=application_names,
            events=events,
        )
        with engine.begin() as connection:
            current_database = connection.scalar(text("SELECT current_database()"))
            if current_database != name:
                raise DatabaseCreationError("workload connection reached an unexpected database")
            connection.execute(text("CREATE SCHEMA p106_harness"))
            connection.execute(
                text(
                    "CREATE TABLE p106_harness.probe ("
                    "probe_id text PRIMARY KEY, "
                    "probe_value text NOT NULL"
                    ")"
                )
            )
        events.append(f"target={name} action=probe-table-created")
        yield harness
    finally:
        if harness is not None:
            harness.close()
        else:
            if lock_key is not None and not maintenance_connection.closed:
                with maintenance_connection.cursor() as cursor:
                    cursor.execute("SELECT pg_advisory_unlock(%s)", (lock_key,))
            maintenance_connection.close()


@dataclass(frozen=True)
class CommittedProbe:
    """Explicit real-commit helper for the exclusively owned harness table."""

    harness: TestDatabaseHarness

    def commit(self, probe_id: str, probe_value: str) -> None:
        with self.harness.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO p106_harness.probe (probe_id, probe_value) "
                    "VALUES (:probe_id, :probe_value)"
                ),
                {"probe_id": probe_id, "probe_value": probe_value},
            )

    def rows(self) -> list[tuple[str, str]]:
        with self.harness.engine.connect() as connection:
            return [
                (str(row.probe_id), str(row.probe_value))
                for row in connection.execute(
                    text("SELECT probe_id, probe_value FROM p106_harness.probe ORDER BY probe_id")
                )
            ]

    def cleanup(self) -> None:
        with self.harness.engine.begin() as connection:
            connection.execute(text("DELETE FROM p106_harness.probe"))
        if self.rows():
            raise DatabaseCleanupError("committed probe cleanup did not leave the table empty")


DatabaseHarnessFactory = Callable[[], AbstractContextManager[TestDatabaseHarness]]

VALID_ENVIRONMENT: dict[str, str] = {
    "ENVIRONMENT": "test",
    "DATABASE_URL": "postgresql+psycopg://postgres:postgres@localhost:5432/business_management_platform_test",
    "JWT_SECRET": "correct-horse-battery-staple-0123456789",
    "JWT_ISSUER": "business-management-platform",
    "JWT_AUDIENCE": "business-management-platform-api",
    "CORS_ALLOWED_ORIGINS": '["http://localhost:5173"]',
    "LOG_LEVEL": "INFO",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
    "REFRESH_TOKEN_EXPIRE_DAYS": "14",
}


@pytest.fixture(autouse=True)
def valid_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in VALID_ENVIRONMENT.items():
        monkeypatch.setenv(name, value)


@pytest.fixture
def test_settings() -> Settings:
    return Settings()


@pytest.fixture
def client(test_settings: Settings) -> Iterator[TestClient]:
    app = create_app(test_settings)
    try:
        with TestClient(app) as managed_client:
            yield managed_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def frozen_time(monkeypatch: pytest.MonkeyPatch) -> FrozenTime:
    def freeze(instant: datetime) -> AbstractContextManager[datetime]:
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("frozen time must be timezone-aware")
        normalized = instant.astimezone(UTC)

        @contextmanager
        def active_freeze() -> Iterator[datetime]:
            with monkeypatch.context() as patch:
                patch.setattr(clock, "utc_now", lambda: normalized)
                yield normalized

        return active_freeze()

    return freeze


@pytest.fixture(scope="session")
def test_database_config() -> TestDatabaseConfig:
    return TestDatabaseConfig.from_environment()


@pytest.fixture(scope="session")
def database_harness_factory(
    test_database_config: TestDatabaseConfig,
) -> DatabaseHarnessFactory:
    def factory() -> AbstractContextManager[TestDatabaseHarness]:
        return create_test_database(test_database_config)

    return factory


@pytest.fixture(scope="session")
def test_database_harness(
    database_harness_factory: DatabaseHarnessFactory,
) -> Iterator[TestDatabaseHarness]:
    with database_harness_factory() as harness:
        yield harness


@pytest.fixture(scope="session")
def db_engine(test_database_harness: TestDatabaseHarness) -> Engine:
    return test_database_harness.engine


@pytest.fixture
def db_session(db_engine: Engine) -> Iterator[Session]:
    connection = db_engine.connect()
    outer_transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        if outer_transaction.is_active:
            outer_transaction.rollback()
        connection.close()


@pytest.fixture
def committed_probe(test_database_harness: TestDatabaseHarness) -> Iterator[CommittedProbe]:
    probe = CommittedProbe(test_database_harness)
    try:
        yield probe
    finally:
        probe.cleanup()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        path_parts = item.path.parts
        if "unit" in path_parts:
            item.add_marker(pytest.mark.unit)
        elif "integration" in path_parts:
            item.add_marker(pytest.mark.integration)
