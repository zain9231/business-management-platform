from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.core import clock
from tests.conftest import FrozenTime


def test_utc_now_returns_aware_utc() -> None:
    now = clock.utc_now()

    assert now.tzinfo is UTC
    assert now.utcoffset() == timedelta(0)


def test_frozen_time_controls_production_clock(frozen_time: FrozenTime) -> None:
    chosen = datetime(2025, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=5)))

    with frozen_time(chosen) as frozen:
        assert frozen == datetime(2025, 2, 2, 23, 5, tzinfo=UTC)
        assert clock.utc_now() == frozen


def test_frozen_time_rejects_naive_datetime(frozen_time: FrozenTime) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        frozen_time(datetime(2025, 2, 3, 4, 5))  # noqa: DTZ001 - deliberately naive input


def test_nested_frozen_time_restores_outer_value(frozen_time: FrozenTime) -> None:
    outer = datetime(2025, 1, 1, tzinfo=UTC)
    inner = datetime(2025, 6, 1, tzinfo=UTC)

    with frozen_time(outer):
        assert clock.utc_now() == outer
        with frozen_time(inner):
            assert clock.utc_now() == inner
        assert clock.utc_now() == outer


def test_frozen_time_restores_clock_after_context(frozen_time: FrozenTime) -> None:
    chosen = datetime(2000, 1, 1, tzinfo=UTC)

    with frozen_time(chosen):
        assert clock.utc_now() == chosen

    assert clock.utc_now() != chosen
