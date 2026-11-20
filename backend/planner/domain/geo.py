"""Geometry on the WGS84 sphere. Internal math in meters; callers convert to miles."""

import itertools
import math
from bisect import bisect_right
from collections.abc import Sequence

import numpy as np
import numpy.typing as npt

from .models import LatLon

EARTH_RADIUS_M = 6_371_008.8


def haversine_m(a: LatLon, b: LatLon) -> float:
    p1, p2 = math.radians(a.lat), math.radians(b.lat)
    dp, dl = p2 - p1, math.radians(b.lon - a.lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def segment_lengths_m(coords: Sequence[LatLon]) -> tuple[float, ...]:
    return tuple(haversine_m(a, b) for a, b in itertools.pairwise(coords))


def cumulative(xs: Sequence[float]) -> tuple[float, ...]:
    """Running sum starting at 0.0, so len(result) == len(xs) + 1."""
    out = [0.0]
    for x in xs:
        out.append(out[-1] + x)
    return tuple(out)


def lerp(a: LatLon, b: LatLon, f: float) -> LatLon:
    """Linear interpolation in lat/lon; fine for route segments of a few km."""
    return LatLon(a.lat + (b.lat - a.lat) * f, a.lon + (b.lon - a.lon) * f)


def initial_bearing_deg(a: LatLon, b: LatLon) -> float:
    p1, p2 = math.radians(a.lat), math.radians(b.lat)
    dl = math.radians(b.lon - a.lon)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def destination_point(start: LatLon, bearing_deg: float, distance_m: float) -> LatLon:
    p1, l1 = math.radians(start.lat), math.radians(start.lon)
    theta, delta = math.radians(bearing_deg), distance_m / EARTH_RADIUS_M
    p2 = math.asin(
        math.sin(p1) * math.cos(delta) + math.cos(p1) * math.sin(delta) * math.cos(theta)
    )
    l2 = l1 + math.atan2(
        math.sin(theta) * math.sin(delta) * math.cos(p1),
        math.cos(delta) - math.sin(p1) * math.sin(p2),
    )
    return LatLon(math.degrees(p2), (math.degrees(l2) + 540.0) % 360.0 - 180.0)


def midpoint(a: LatLon, b: LatLon) -> LatLon:
    p1, l1 = math.radians(a.lat), math.radians(a.lon)
    p2, dl = math.radians(b.lat), math.radians(b.lon - a.lon)
    bx, by = math.cos(p2) * math.cos(dl), math.cos(p2) * math.sin(dl)
    p3 = math.atan2(math.sin(p1) + math.sin(p2), math.hypot(math.cos(p1) + bx, by))
    l3 = l1 + math.atan2(by, math.cos(p1) + bx)
    return LatLon(math.degrees(p3), math.degrees(l3))


def slice_by_distance(
    coords: Sequence[LatLon], cum_dist_m: Sequence[float], start_m: float, end_m: float
) -> list[LatLon]:
    """Sub-line between two distances along the route, with interpolated end points."""

    def point_at(target: float) -> tuple[int, LatLon]:
        i = min(max(bisect_right(cum_dist_m, target) - 1, 0), len(coords) - 2)
        seg = cum_dist_m[i + 1] - cum_dist_m[i]
        f = 0.0 if seg == 0 else (target - cum_dist_m[i]) / seg
        return i, lerp(coords[i], coords[i + 1], min(max(f, 0.0), 1.0))

    i0, p0 = point_at(start_m)
    i1, p1 = point_at(end_m)
    return [p0, *coords[i0 + 1 : i1 + 1], p1]


# --- Projection and simplification ---

FloatArray = npt.NDArray[np.float64]


def project_equirectangular(coords: Sequence[LatLon], lat0: float) -> FloatArray:
    """(n, 2) array of meters, x east and y north, centered on lat0. Accurate enough for
    distances of a few km within one corridor (docs/03 §3)."""
    arr = np.array([(c.lon, c.lat) for c in coords], dtype=np.float64).reshape(-1, 2)
    k = math.radians(1.0) * EARTH_RADIUS_M
    arr[:, 0] *= k * math.cos(math.radians(lat0))
    arr[:, 1] *= k
    return arr


def _dp_keep(xy: FloatArray, tolerance_m: float) -> npt.NDArray[np.bool_]:
    """Douglas-Peucker on projected points; iterative so long routes don't recurse."""
    keep = np.zeros(len(xy), dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(xy) - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        seg = xy[b] - xy[a]
        pts = xy[a + 1 : b] - xy[a]
        seg_len = float(np.hypot(seg[0], seg[1]))
        if seg_len == 0.0:
            dist = np.hypot(pts[:, 0], pts[:, 1])
        else:
            dist = np.abs(seg[0] * pts[:, 1] - seg[1] * pts[:, 0]) / seg_len
        i = int(np.argmax(dist))
        if dist[i] > tolerance_m:
            mid = a + 1 + i
            keep[mid] = True
            stack.extend(((a, mid), (mid, b)))
    return keep


def simplify_indices(
    coords: Sequence[LatLon], max_vertices: int, tolerance_m: float = 15.0
) -> tuple[int, ...]:
    """Indices of the vertices to keep (always the two ends), at most `max_vertices`.
    Returning indices lets callers keep per-vertex data such as cumulative time aligned."""
    n = len(coords)
    xy = project_equirectangular(coords, sum(c.lat for c in coords) / n)
    tol = tolerance_m
    while True:
        keep = _dp_keep(xy, tol)
        if int(keep.sum()) <= max_vertices:
            return tuple(int(i) for i in np.flatnonzero(keep))
        tol *= 1.6
