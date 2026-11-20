import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from planner.domain import geo
from planner.domain.models import LatLon

DEN = LatLon(39.7392, -104.9903)
SLC = LatLon(40.7608, -111.8910)


def test_haversine_denver_slc() -> None:
    assert geo.haversine_m(DEN, SLC) == pytest.approx(596_400, rel=0.002)
    assert geo.haversine_m(DEN, DEN) == 0.0


def test_one_degree_of_latitude() -> None:
    assert geo.haversine_m(LatLon(0, 0), LatLon(1, 0)) == pytest.approx(111_195, rel=1e-3)


def test_segment_lengths_and_cumulative() -> None:
    coords = (LatLon(0, 0), LatLon(0, 1), LatLon(0, 1), LatLon(0, 2))
    seg = geo.segment_lengths_m(coords)
    assert len(seg) == 3 and seg[1] == 0.0
    assert geo.cumulative(seg)[-1] == pytest.approx(2 * 111_195, rel=1e-3)


def test_lerp() -> None:
    assert geo.lerp(LatLon(0, 0), LatLon(10, 20), 0.25) == LatLon(2.5, 5.0)


def test_bearing_and_destination_round_trip() -> None:
    bearing = geo.initial_bearing_deg(DEN, SLC)
    assert 270 < bearing < 290
    there = geo.destination_point(DEN, bearing, geo.haversine_m(DEN, SLC))
    assert geo.haversine_m(there, SLC) < 1.0
    assert geo.initial_bearing_deg(LatLon(0, 0), LatLon(1, 0)) == pytest.approx(0.0)
    assert geo.initial_bearing_deg(LatLon(0, 0), LatLon(0, -1)) == pytest.approx(270.0)


def test_midpoint_is_equidistant() -> None:
    mid = geo.midpoint(DEN, SLC)
    assert geo.haversine_m(DEN, mid) == pytest.approx(geo.haversine_m(mid, SLC), rel=1e-9)


def test_slice_by_distance_includes_interpolated_ends() -> None:
    coords = (LatLon(0, 0), LatLon(0, 1), LatLon(0, 2), LatLon(0, 3))
    cum = geo.cumulative(geo.segment_lengths_m(coords))
    part = geo.slice_by_distance(coords, cum, cum[1] / 2, cum[2] + (cum[3] - cum[2]) / 2)
    assert part[0].lon == pytest.approx(0.5)
    assert [p.lon for p in part[1:-1]] == [1.0, 2.0]
    assert part[-1].lon == pytest.approx(2.5)


def test_slice_inside_one_segment_has_two_points() -> None:
    coords = (LatLon(0, 0), LatLon(0, 1))
    cum = geo.cumulative(geo.segment_lengths_m(coords))
    part = geo.slice_by_distance(coords, cum, cum[1] * 0.2, cum[1] * 0.4)
    assert len(part) == 2
    assert part[0].lon == pytest.approx(0.2) and part[1].lon == pytest.approx(0.4)


def zigzag(n: int) -> tuple[LatLon, ...]:
    return tuple(LatLon(40 + 0.001 * (i % 2), -105 + i * 0.01) for i in range(n))


def test_simplify_keeps_endpoints_and_respects_budget() -> None:
    coords = zigzag(5_000)
    keep = geo.simplify_indices(coords, max_vertices=300)
    assert keep[0] == 0 and keep[-1] == len(coords) - 1
    assert len(keep) <= 300
    assert list(keep) == sorted(set(keep))


def test_simplify_short_line_is_identity() -> None:
    coords = zigzag(10)
    assert geo.simplify_indices(coords, max_vertices=2000) == tuple(range(10))


def test_simplify_drops_collinear_points() -> None:
    coords = tuple(LatLon(40, -105 + i * 0.01) for i in range(100))
    assert geo.simplify_indices(coords, max_vertices=2000, tolerance_m=1.0) == (0, 99)


@given(st.lists(st.floats(-60, 60), min_size=2, max_size=2), st.floats(0, 359.9))
def test_destination_distance_matches_haversine(latlon: list[float], bearing: float) -> None:
    start = LatLon(latlon[0], latlon[1])
    end = geo.destination_point(start, bearing, 50_000)
    assert math.isclose(geo.haversine_m(start, end), 50_000, rel_tol=1e-6)


def test_simplify_handles_closed_loop_segments() -> None:
    # First and last points coincide: the DP baseline has zero length.
    loop = (LatLon(40, -105), LatLon(40.1, -105), LatLon(40.1, -104.9), LatLon(40, -105))
    keep = geo.simplify_indices(loop, max_vertices=10, tolerance_m=1.0)
    assert keep == (0, 1, 2, 3)
