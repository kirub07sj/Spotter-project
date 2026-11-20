import itertools

import pytest
from hypothesis import given
from hypothesis import strategies as st

from planner.domain.attribution import owned_intervals, risk_runs, route_stats
from planner.domain.levels import Level
from planner.domain.sampling import checkpoint_miles


def test_two_checkpoints_split_at_midpoint() -> None:
    assert owned_intervals([0.0, 10.0], 10.0) == [(0.0, 5.0), (5.0, 10.0)]


def test_single_checkpoint_owns_everything() -> None:
    assert owned_intervals([0.0], 42.0) == [(0.0, 42.0)]


def test_regular_spacing() -> None:
    assert owned_intervals([0.0, 25.0, 50.0, 75.0, 100.0], 100.0) == [
        (0.0, 12.5),
        (12.5, 37.5),
        (37.5, 62.5),
        (62.5, 87.5),
        (87.5, 100.0),
    ]


def test_empty_checkpoints_rejected() -> None:
    with pytest.raises(ValueError):
        owned_intervals([], 10.0)


@given(st.floats(0.6, 3000), st.sampled_from([10, 25, 50]))
def test_owned_miles_sum_to_route_length(total: float, interval: int) -> None:
    intervals = owned_intervals(checkpoint_miles(total, interval), total)
    assert sum(r - left for left, r in intervals) == pytest.approx(total, abs=1e-9)
    assert intervals[0][0] == 0.0 and intervals[-1][1] == total
    assert all(a[1] == b[0] for a, b in itertools.pairwise(intervals))


def test_route_stats_distance_weighted() -> None:
    intervals = owned_intervals([0.0, 25.0, 50.0, 75.0, 100.0], 100.0)
    levels = [Level.LOW, Level.HIGH, Level.SEVERE, Level.LOW, Level.MODERATE]
    stats = route_stats(intervals, levels)
    assert stats.miles_by_level[Level.LOW] == pytest.approx(37.5)
    assert stats.miles_by_level[Level.HIGH] == pytest.approx(25.0)
    assert stats.miles_by_level[Level.SEVERE] == pytest.approx(25.0)
    assert stats.miles_by_level[Level.MODERATE] == pytest.approx(12.5)
    assert stats.miles_by_level[Level.NO_TRAVEL] == 0.0
    assert stats.avg_risk == pytest.approx((25 * 2 + 25 * 3 + 12.5 * 1) / 100)  # D-10
    assert stats.max_level is Level.SEVERE
    assert stats.unknown_mi == 0.0


def test_unknown_miles_are_excluded_from_stats() -> None:
    intervals = owned_intervals([0.0, 10.0, 20.0], 20.0)
    stats = route_stats(intervals, [Level.HIGH, Level.UNKNOWN, Level.LOW])
    assert stats.unknown_mi == pytest.approx(10.0)
    assert sum(stats.miles_by_level.values()) == pytest.approx(10.0)
    assert stats.avg_risk == pytest.approx(1.0)  # (5 * 2 + 5 * 0) / 10
    assert stats.max_level is Level.HIGH


def test_all_unknown_route() -> None:
    stats = route_stats(owned_intervals([0.0, 10.0], 10.0), [Level.UNKNOWN, Level.UNKNOWN])
    assert stats.avg_risk == 0.0 and stats.max_level is Level.UNKNOWN
    assert stats.unknown_mi == pytest.approx(10.0)


def test_stats_reject_mismatched_lengths() -> None:
    with pytest.raises(ValueError):
        route_stats([(0.0, 1.0)], [Level.LOW, Level.LOW])


def test_risk_runs_merge_neighbours_with_same_level() -> None:
    intervals = owned_intervals([0.0, 25.0, 50.0, 75.0, 100.0], 100.0)
    levels = [Level.LOW, Level.HIGH, Level.HIGH, Level.LOW, Level.LOW]
    runs = risk_runs(intervals, levels)
    assert [(r.from_mi, r.to_mi, r.level) for r in runs] == [
        (0.0, 12.5, Level.LOW),
        (12.5, 62.5, Level.HIGH),
        (62.5, 100.0, Level.LOW),
    ]


def test_risk_runs_empty() -> None:
    assert risk_runs([], []) == []
