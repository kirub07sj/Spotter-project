import pytest

from planner.domain.alternatives import (
    candidate_via_points,
    needs_more_routes,
    overlap_ratio,
    select_routes,
)
from planner.domain.geo import haversine_m, midpoint, segment_lengths_m
from planner.domain.models import LatLon, RouteGeometry

ORIGIN = LatLon(40.0, -105.0)
DEST = LatLon(40.0, -100.0)


def line(
    lat: float, n: int = 200, lon0: float = -105.0, lon1: float = -100.0
) -> tuple[LatLon, ...]:
    return tuple(LatLon(lat, lon0 + (lon1 - lon0) * i / n) for i in range(n + 1))


def route(coords: tuple[LatLon, ...], speed_mps: float = 30.0) -> RouteGeometry:
    seg = segment_lengths_m(coords)
    return RouteGeometry(coords, seg, tuple(d / speed_mps for d in seg), "")


def test_via_points_are_perpendicular_offsets_in_fixed_order() -> None:
    vias = candidate_via_points(ORIGIN, DEST)
    mid = midpoint(ORIGIN, DEST)
    dist = haversine_m(ORIGIN, DEST)
    assert len(vias) == 4
    # Eastbound trip: +90 degrees is south, so +0.15 lies south of the midpoint.
    assert vias[0].lat < mid.lat < vias[1].lat
    assert haversine_m(mid, vias[0]) == pytest.approx(0.15 * dist, rel=1e-6)
    assert haversine_m(mid, vias[2]) == pytest.approx(0.30 * dist, rel=1e-6)


def test_overlap_identical_and_disjoint() -> None:
    assert overlap_ratio(line(40.0), line(40.0)) == 1.0
    assert overlap_ratio(line(40.0), line(41.0)) == 0.0


def test_overlap_within_tolerance_counts() -> None:
    assert overlap_ratio(line(40.0), line(40.01)) == 1.0  # ~1.1 km apart: within 1.5 km
    assert overlap_ratio(line(40.0), line(40.02)) == 0.0  # ~2.2 km apart


def test_partial_overlap() -> None:
    half = line(40.0, lon1=-102.5)
    assert overlap_ratio(line(40.0), half) == pytest.approx(0.5, abs=0.02)


def test_select_dedupes_provider_near_duplicates() -> None:
    a, dup = route(line(40.0)), route(line(40.005), 29.0)
    picked = select_routes([a, dup], [])
    assert [p.geometry for p in picked] == [a]
    assert needs_more_routes([a, dup]) is True


def test_select_fills_with_via_routes_in_order_and_sorts_by_duration() -> None:
    a = route(line(40.0), 30.0)
    via_slow = route(line(40.5), 25.0)
    via_fast = route(line(39.5), 28.0)
    picked = select_routes([a], [via_slow, via_fast, route(line(41.0), 26.0)])
    assert [p.source for p in picked] == ["provider", "via", "via"]
    assert [p.geometry for p in picked] == [a, via_fast, via_slow]


def test_select_skips_failed_overlapping_and_unreasonable_detours() -> None:
    a = route(line(40.0), 30.0)
    b = route(line(40.5), 30.0)
    overlapping = route(line(40.003), 30.0)
    detour = route(line(39.0), 19.0)  # 30/19 = 1.58x the fastest duration
    ok = route(line(39.5), 21.0)  # 1.43x: accepted
    picked = select_routes([a, b], [None, overlapping, detour, ok])
    geoms = [p.geometry for p in picked]
    assert len(geoms) == 3 and all(any(g is r for g in geoms) for r in (a, b, ok))
    assert [g.duration_s for g in geoms] == sorted(g.duration_s for g in geoms)


def test_select_stops_at_three() -> None:
    routes = [route(line(40.0 + i)) for i in range(3)]
    picked = select_routes(routes, [route(line(45.0))])
    assert len(picked) == 3
    assert needs_more_routes(routes) is False


def test_select_with_no_primary_routes() -> None:
    assert select_routes([], [route(line(40.0))]) == []
