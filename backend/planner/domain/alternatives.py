"""Getting 3 distinct routes (D-13, docs/03 §3)."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
import shapely

from .geo import (
    cumulative,
    destination_point,
    haversine_m,
    initial_bearing_deg,
    midpoint,
    project_equirectangular,
    segment_lengths_m,
)
from .models import LatLon, RouteGeometry

RouteSource = Literal["provider", "via"]

VIA_OFFSET_FRACTIONS = (0.15, -0.15, 0.30, -0.30)
MAX_DETOUR_RATIO = 1.5
MAX_OVERLAP_RATIO = 0.80
OVERLAP_SAMPLE_STEP_M = 1_000.0
OVERLAP_NEAR_M = 1_500.0
TARGET_ROUTES = 3


@dataclass(frozen=True, slots=True)
class RouteCandidate:
    geometry: RouteGeometry
    source: RouteSource


def candidate_via_points(origin: LatLon, dest: LatLon) -> list[LatLon]:
    """Points offset perpendicular to the straight line, at its midpoint."""
    distance = haversine_m(origin, dest)
    mid = midpoint(origin, dest)
    bearing = initial_bearing_deg(origin, dest)
    return [destination_point(mid, bearing + 90.0, f * distance) for f in VIA_OFFSET_FRACTIONS]


def _sample_every(coords: Sequence[LatLon], step_m: float) -> list[LatLon]:
    cum = cumulative(segment_lengths_m(coords))
    total = cum[-1]
    n = max(int(total // step_m), 1)
    targets = np.linspace(0.0, total, n + 1)
    lats = np.interp(targets, cum, [c.lat for c in coords])
    lons = np.interp(targets, cum, [c.lon for c in coords])
    return [LatLon(float(a), float(b)) for a, b in zip(lats, lons, strict=True)]


def overlap_ratio(a: Sequence[LatLon], b: Sequence[LatLon]) -> float:
    """Share of 1 km samples along `a` that lie within 1.5 km of polyline `b`."""
    samples = _sample_every(a, OVERLAP_SAMPLE_STEP_M)
    lat0 = (samples[0].lat + samples[-1].lat) / 2
    pts = project_equirectangular(samples, lat0)
    line = project_equirectangular(b, lat0)
    segments = shapely.linestrings(np.stack([line[:-1], line[1:]], axis=1))
    tree = shapely.STRtree(segments)
    hits = tree.query(shapely.points(pts), predicate="dwithin", distance=OVERLAP_NEAR_M)
    return float(len(np.unique(hits[0]))) / len(samples)


def _is_distinct(cand: RouteGeometry, accepted: Iterable[RouteCandidate]) -> bool:
    return all(overlap_ratio(cand.coords, r.geometry.coords) <= MAX_OVERLAP_RATIO for r in accepted)


def select_routes(
    primary: Sequence[RouteGeometry], via_candidates: Sequence[RouteGeometry | None]
) -> list[RouteCandidate]:
    """Provider routes first (deduped), then via candidates in the fixed order of
    VIA_OFFSET_FRACTIONS, so the result is deterministic. Sorted by provider duration."""
    accepted: list[RouteCandidate] = []
    for route in primary:
        if _is_distinct(route, accepted):
            accepted.append(RouteCandidate(route, "provider"))
    if not accepted:
        return []
    fastest = min(r.geometry.duration_s for r in accepted)
    for cand in via_candidates:
        if len(accepted) >= TARGET_ROUTES:
            break
        if cand is None or cand.duration_s > MAX_DETOUR_RATIO * fastest:
            continue
        if _is_distinct(cand, accepted):
            accepted.append(RouteCandidate(cand, "via"))
    return sorted(accepted, key=lambda r: r.geometry.duration_s)


def needs_more_routes(primary: Sequence[RouteGeometry]) -> bool:
    return len(select_routes(primary, [])) < TARGET_ROUTES
