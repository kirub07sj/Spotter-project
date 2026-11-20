"""polyline6 encoding for the API contract."""

from collections.abc import Sequence

import polyline

from planner.domain.models import LatLon

PRECISION = 6


def encode(coords: Sequence[LatLon]) -> str:
    return str(polyline.encode([(c.lat, c.lon) for c in coords], PRECISION))


def decode(encoded: str) -> list[LatLon]:
    return [LatLon(lat, lon) for lat, lon in polyline.decode(encoded, PRECISION)]
