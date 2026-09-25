import threading

import psycopg
import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from tests.conftest import (
    CommittedProbe,
    DatabaseCleanupError,
    DatabaseHarnessFactory,
    TestDatabaseHarness,
)


def _probe_rows(engine: Engine) -> list[tuple[str, str]]:
    with engine.connect() as connection:
        return [
            (str(row.probe_id), str(row.probe_value))
            for row in connection.execute(
                text("SELECT probe_id, probe_value FROM p106_harness.probe ORDER BY probe_id")
            )
        ]


def _unrelated_databases(catalog: dict[str, int]) -> dict[str, int]:
    return {name: oid for name, oid in catalog.items() if not name.startswith("bmp_test_")}


def test_run_database_has_recorded_identity_and_only_the_probe_schema(
    test_database_harness: TestDatabaseHarness,
) -> None:
    with test_database_harness.engine.connect() as connection:
        database_name = connection.scalar(text("SELECT current_database()"))
        harness_tables = [
            (str(row.table_schema), str(row.table_name))
            for row in connection.execute(
                text(
                    "SELECT table_schema, table_name FROM information_schema.tables "
                    "WHERE table_schema NOT IN ('pg_catalog', 'information_schema') "
                    "ORDER BY table_schema, table_name"
                )
            )
        ]

    assert database_name == test_database_harness.name
    assert harness_tables == [("p106_harness", "probe")]
    assert test_database_harness.oid > 0
    assert test_database_harness.events[:3] == [
        f"target={test_database_harness.name} action=advisory-lock-acquired",
        f"target={test_database_harness.name} action=absence-confirmed",
        f"target={test_database_harness.name} action=database-created",
    ]


def test_session_commit_remains_inside_the_outer_transaction(
    db_session: Session,
    db_engine: Engine,
) -> None:
    db_session.execute(
        text(
            "INSERT INTO p106_harness.probe (probe_id, probe_value) "
            "VALUES (:probe_id, :probe_value)"
        ),
        {"probe_id": "rollback-a", "probe_value": "not externally committed"},
    )
    db_session.commit()

    assert _probe_rows(db_engine) == []


def test_outer_transaction_removed_the_previous_test_write(db_engine: Engine) -> None:
    assert _probe_rows(db_engine) == []


def test_session_rollback_removes_pending_work(db_session: Session, db_engine: Engine) -> None:
    db_session.execute(
        text(
            "INSERT INTO p106_harness.probe (probe_id, probe_value) "
            "VALUES (:probe_id, :probe_value)"
        ),
        {"probe_id": "rollback-b", "probe_value": "rolled back"},
    )
    db_session.rollback()

    assert _probe_rows(db_engine) == []


def test_committed_isolation_a(committed_probe: CommittedProbe) -> None:
    assert committed_probe.rows() == []

    committed_probe.commit("committed-a", "visible from another connection")

    assert committed_probe.rows() == [("committed-a", "visible from another connection")]


def test_committed_isolation_b(committed_probe: CommittedProbe) -> None:
    assert committed_probe.rows() == []

    committed_probe.commit("committed-b", "also independently visible")

    assert committed_probe.rows() == [("committed-b", "also independently visible")]


@pytest.mark.concurrency
def test_concurrent_runs_own_distinct_databases_and_teardown_is_independent(
    database_harness_factory: DatabaseHarnessFactory,
) -> None:
    ready = threading.Barrier(3)
    release = [threading.Event(), threading.Event()]
    harnesses: list[TestDatabaseHarness | None] = [None, None]
    errors: list[Exception] = []

    def run_harness(index: int) -> None:
        try:
            with database_harness_factory() as harness:
                harnesses[index] = harness
                ready.wait(timeout=30)
                if not release[index].wait(timeout=30):
                    raise TimeoutError("concurrent harness release was not signaled")
        except Exception as exc:  # noqa: BLE001 - surface worker teardown failures in main thread
            errors.append(exc)
            ready.abort()

    workers = [threading.Thread(target=run_harness, args=(index,)) for index in range(2)]
    for worker in workers:
        worker.start()
    try:
        ready.wait(timeout=30)
        first, second = harnesses
        assert first is not None
        assert second is not None
        assert first.name != second.name
        release[0].set()
        workers[0].join(timeout=30)
        assert not workers[0].is_alive()
        assert errors == []

        with second.engine.connect() as connection:
            assert connection.scalar(text("SELECT current_database()")) == second.name
    finally:
        for event in release:
            event.set()
        for worker in workers:
            worker.join(timeout=30)

    assert not any(worker.is_alive() for worker in workers)
    assert errors == []


def test_unrelated_catalog_identities_are_unchanged(
    test_database_harness: TestDatabaseHarness,
    database_harness_factory: DatabaseHarnessFactory,
) -> None:
    before = _unrelated_databases(test_database_harness.catalog_snapshot())

    with database_harness_factory() as temporary:
        during = test_database_harness.catalog_snapshot()
        assert during[temporary.name] == temporary.oid
        assert _unrelated_databases(during) == before

    assert _unrelated_databases(test_database_harness.catalog_snapshot()) == before


def test_exception_path_drops_the_owned_database(
    test_database_harness: TestDatabaseHarness,
    database_harness_factory: DatabaseHarnessFactory,
) -> None:
    created_name = ""

    with (
        pytest.raises(RuntimeError, match="deliberate setup/test failure"),
        database_harness_factory() as temporary,
    ):
        created_name = temporary.name
        raise RuntimeError("deliberate setup/test failure")

    assert created_name not in test_database_harness.catalog_snapshot()
    assert temporary.events[-1] == f"target={created_name} action=database-dropped"


def test_active_connection_refuses_drop_without_terminating_the_client(
    database_harness_factory: DatabaseHarnessFactory,
) -> None:
    with database_harness_factory() as temporary:
        try:
            client = psycopg.connect(
                temporary.connection_string,
                application_name="p106-active-refusal-proof",
            )
        except psycopg.Error:
            client = None
        if client is None:
            raise AssertionError("could not connect the active client") from None
        try:
            with pytest.raises(DatabaseCleanupError, match="active connection"):
                temporary.assert_safe_to_drop()
            with client.cursor() as cursor:
                cursor.execute("SELECT current_database()")
                assert cursor.fetchone() == (temporary.name,)
        finally:
            client.close()
