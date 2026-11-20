import itertools
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from hypothesis import given
from hypothesis import strategies as st

from planner.domain.geo import cumulative, segment_lengths_m
from planner.domain.models import LatLon
from planner.domain.sampling import checkpoint_miles, locate, sample_checkpoints
from planner.domain.units import M_PER_MI

DEPART = datetime(2026, 11, 20, 13, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("total", "interval", "expected"),
    [
        (100.0, 25, [0.0, 25.0, 50.0, 75.0, 100.0]),
        (101.0, 25, [0.0, 25.0, 50.0, 75.0, 100.0, 101.0]),
        (100.4, 25, [0.0, 25.0, 50.0, 75.0, 100.4]),  # 100 is < 0.5 mi before the end (D-06)
        (100.5, 25, [0.0, 25.0, 50.0, 75.0, 100.0, 100.5]),  # exactly 0.5 mi: kept
        (8.0, 10, [0.0, 8.0]),  # shorter than one interval: origin + destination
        (30.0, 10, [0.0, 10.0, 20.0, 30.0]),
    ],
)
def test_checkpoint_miles(total: float, interval: int, expected: list[float]) -> None:
    assert checkpoint_miles(total, interval) == expected


@given(st.floats(0.6, 3000), st.sampled_from([10, 25, 50]))
def test_checkpoint_miles_properties(total: float, interval: int) -> None:
    miles = checkpoint_miles(total, interval)
    assert miles[0] == 0.0 and miles[-1] == total
    assert all(b > a for a, b in itertools.pairwise(miles))
    assert miles[-1] - miles[-2] >= 0.5 or len(miles) == 2


def straight_route(n_segments: int, seg_lon: float = 0.1) -> tuple[tuple[LatLon, ...], ...]:
    coords = tuple(LatLon(40.0, -105.0 + i * seg_lon) for i in range(n_segments + 1))
    return (coords,)


def test_locate_interpolates_position_and_time() -> None:
    coords = (LatLon(0, 0), LatLon(0, 1), LatLon(0, 2))
    cum_d = (0.0, 100.0, 200.0)
    cum_t = (0.0, 10.0, 30.0)
    point, t = locate(cum_d, cum_t, coords, 150.0)
    assert point.lon == pytest.approx(1.5)
    assert t == pytest.approx(20.0)


def test_locate_handles_zero_length_segment_and_ends() -> None:
    coords = (LatLon(0, 0), LatLon(0, 0), LatLon(0, 1))
    cum_d = (0.0, 0.0, 100.0)
    cum_t = (0.0, 5.0, 15.0)
    p0, t0 = locate(cum_d, cum_t, coords, 0.0)
    assert p0 == LatLon(0, 0) and t0 == pytest.approx(5.0)
    p_end, t_end = locate(cum_d, cum_t, coords, 100.0)
    assert p_end.lon == pytest.approx(1.0) and t_end == pytest.approx(15.0)
    p_past, _ = locate(cum_d, cum_t, coords, 150.0)  # clamped to the last segment
    assert p_past.lon == pytest.approx(1.5)


def test_sample_checkpoints_etas_increase_and_end_at_destination() -> None:
    (coords,) = straight_route(40)
    seg = segment_lengths_m(coords)
    cum_d = cumulative(seg)
    cum_t = cumulative(tuple(d / 25.0 for d in seg))  # 25 m/s everywhere
    cps = sample_checkpoints(coords, cum_d, cum_t, DEPART, 25)
    total_mi = cum_d[-1] / M_PER_MI
    assert [cp.index for cp in cps] == list(range(len(cps)))
    assert cps[0].mile == 0.0 and cps[0].eta == DEPART and cps[0].position == coords[0]
    assert cps[-1].mile == pytest.approx(total_mi)
    assert cps[-1].eta == DEPART + timedelta(seconds=cum_t[-1])
    assert all(b.eta > a.eta for a, b in itertools.pairwise(cps))
    assert cps[1].eta - DEPART == timedelta(seconds=25 * M_PER_MI / 25.0)


def test_sample_rejects_naive_departure() -> None:
    (coords,) = straight_route(2)
    cum = cumulative(segment_lengths_m(coords))
    with pytest.raises(ValueError, match="aware"):
        sample_checkpoints(coords, cum, cum, datetime(2026, 1, 1), 25)


def test_trip_across_midnight_and_dst_is_plain_utc_arithmetic() -> None:
    # 2026-11-01 is the US DST end. Departure given in Denver time, 23:30 the night before.
    depart_local = datetime(2026, 10, 31, 23, 30, tzinfo=ZoneInfo("America/Denver"))
    (coords,) = straight_route(10)
    seg = segment_lengths_m(coords)
    cum_d = cumulative(seg)
    cum_t = cumulative(tuple(3600.0 for _ in seg))  # 1 h per segment, 10 h trip
    cps = sample_checkpoints(coords, cum_d, cum_t, depart_local, 50)
    assert all(cp.eta.tzinfo is UTC for cp in cps)
    assert cps[-1].eta - cps[0].eta == timedelta(hours=10)
    assert cps[0].eta == datetime(2026, 11, 1, 5, 30, tzinfo=UTC)
