import pytest

from planner.domain.eta import capped_durations, cumulative
from planner.domain.units import mph_to_mps


def test_cap_slows_segments_faster_than_cap() -> None:
    dist = (1609.344, 1609.344)  # one mile each
    dur = (36.0, 120.0)  # 100 mph, then 30 mph
    capped = capped_durations(dist, dur, 65)
    assert capped[0] == pytest.approx(1609.344 / mph_to_mps(65))
    assert capped[1] == 120.0


def test_cap_disabled_with_zero() -> None:
    assert capped_durations((1000.0,), (1.0,), 0) == (1.0,)


def test_cumulative_starts_at_zero() -> None:
    assert cumulative((1.0, 2.0, 3.0)) == (0.0, 1.0, 3.0, 6.0)
    assert cumulative(()) == (0.0,)
