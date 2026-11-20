"""Deterministic providers for tests and offline dev (`PROVIDERS=fake`). They return data
in the same shape and units as the real adapters, so the rest of the app can't tell."""

import math
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from planner.domain.errors import NoRouteError
from planner.domain.geo import haversine_m, segment_lengths_m
from planner.domain.models import HourlySeries, LatLon, Place, RouteGeometry
from planner.domain.units import cm_to_in, kmh_to_mph, mm_to_in

from .mapbox_geocoding import normalize_query

# Rough drivable North America; anything outside (e.g. across an ocean) has no route.
_LAND = (15.0, 72.0, -170.0, -50.0)
_STEP_M = 1_000.0
_URBAN_M = 8_000.0


def _on_land(p: LatLon) -> bool:
    return _LAND[0] <= p.lat <= _LAND[1] and _LAND[2] <= p.lon <= _LAND[3]


def _bezier(a: LatLon, ctrl: LatLon, b: LatLon) -> tuple[LatLon, ...]:
    n = max(int(haversine_m(a, b) / _STEP_M), 2)
    pts = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        pts.append(
            LatLon(
                u * u * a.lat + 2 * u * t * ctrl.lat + t * t * b.lat,
                u * u * a.lon + 2 * u * t * ctrl.lon + t * t * b.lon,
            )
        )
    return tuple(pts)


def _route(coords: tuple[LatLon, ...], cruise_mps: float, summary: str) -> RouteGeometry:
    dist = segment_lengths_m(coords)
    total = sum(dist)
    travelled, durations = 0.0, []
    for d in dist:
        urban = travelled < _URBAN_M or total - travelled < _URBAN_M
        durations.append(d / (13.0 if urban else cruise_mps))
        travelled += d
    return RouteGeometry(coords, dist, tuple(durations), summary)


class FakeRouting:
    """A fast primary plus one alternative, like Mapbox often returns, so the via-point
    fallback (D-13) is exercised in offline dev too."""

    ALTERNATIVES = ((0.0, 31.3, "I 80"), (-0.12, 27.0, "US 40"))  # offset, cruise m/s, name

    async def route(
        self,
        origin: LatLon,
        destination: LatLon,
        *,
        via: LatLon | None = None,
        alternatives: bool = True,
        load_lb: float = 0.0,
    ) -> list[RouteGeometry]:
        if not (_on_land(origin) and _on_land(destination)) or (via and not _on_land(via)):
            raise NoRouteError("No drivable route was found between these points.")
        mid = LatLon((origin.lat + destination.lat) / 2, (origin.lon + destination.lon) / 2)
        if via is not None:
            ctrl = LatLon(2 * via.lat - mid.lat, 2 * via.lon - mid.lon)  # curve passes via
            return [_route(_bezier(origin, ctrl, destination), 28.0, "US 6")]
        dlat, dlon = destination.lat - origin.lat, destination.lon - origin.lon
        out = []
        for offset, speed, name in self.ALTERNATIVES[: 2 if alternatives else 1]:
            ctrl = LatLon(mid.lat - dlon * offset * 2, mid.lon + dlat * offset * 2)
            out.append(_route(_bezier(origin, ctrl, destination), speed, name))
        return out


class FakeWeather:
    """Smooth, deterministic fields of (lat, lon, hour), mostly Low with Moderate patches.
    Built in metric and converted like the real adapter."""

    async def hourly(
        self, points: Sequence[LatLon], start: datetime, end: datetime
    ) -> list[HourlySeries]:
        first = start.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
        hours = int((end - first).total_seconds() // 3600) + 1
        times = [first + timedelta(hours=i) for i in range(hours)]
        return [self._series(round(p.lat, 2), round(p.lon, 2), times) for p in points]

    @staticmethod
    def _series(lat: float, lon: float, times: list[datetime]) -> HourlySeries:
        wind, gust, rain, snow = [], [], [], []
        for t in times:
            h = t.timestamp() / 3600.0
            # Peaks near 34 mph (Moderate) so Severe and No Travel come from the demo
            # scenarios, not from the fake baseline.
            gust_kmh = (
                15
                + 28 * max(0.0, math.sin(lat * 0.9 + lon * 0.35 + h * 0.11))
                + 12 * math.sin(lon * 0.9 - h * 0.05) ** 2
            )
            rain_mm = max(0.0, 6 * math.sin(lat * 1.3 - lon * 0.4 + h * 0.07) - 2)
            snow_cm = max(0.0, 3.5 * math.sin(lat * 0.8 + lon * 0.9 - h * 0.09) - 1.5)
            gust.append(kmh_to_mph(gust_kmh))
            wind.append(kmh_to_mph(gust_kmh * 0.6))
            rain.append(mm_to_in(rain_mm if lat <= 41 else rain_mm / 3))
            snow.append(cm_to_in(snow_cm if lat > 38 else 0.0))
        return HourlySeries(
            times=tuple(int(t.timestamp()) for t in times),
            wind_mph=tuple(wind),
            gust_mph=tuple(gust),
            rain_in_hr=tuple(rain),
            snow_in_hr=tuple(snow),
        )


_CITIES = [
    ("Denver, Colorado, United States", 39.7392, -104.9903),
    ("Salt Lake City, Utah, United States", 40.7608, -111.8910),
    ("Cheyenne, Wyoming, United States", 41.1400, -104.8202),
    ("Chicago, Illinois, United States", 41.8781, -87.6298),
    ("Dallas, Texas, United States", 32.7767, -96.7970),
    ("Houston, Texas, United States", 29.7604, -95.3698),
    ("Kansas City, Missouri, United States", 39.0997, -94.5786),
    ("Minneapolis, Minnesota, United States", 44.9778, -93.2650),
    ("Omaha, Nebraska, United States", 41.2565, -95.9345),
    ("Albuquerque, New Mexico, United States", 35.0844, -106.6504),
    ("Phoenix, Arizona, United States", 33.4484, -112.0740),
    ("Las Vegas, Nevada, United States", 36.1699, -115.1398),
    ("Los Angeles, California, United States", 34.0522, -118.2437),
    ("Reno, Nevada, United States", 39.5296, -119.8138),
    ("Boise, Idaho, United States", 43.6150, -116.2023),
    ("Billings, Montana, United States", 45.7833, -108.5007),
    ("Seattle, Washington, United States", 47.6062, -122.3321),
    ("Portland, Oregon, United States", 45.5152, -122.6784),
    ("Atlanta, Georgia, United States", 33.7490, -84.3880),
    ("Nashville, Tennessee, United States", 36.1627, -86.7816),
    ("St. Louis, Missouri, United States", 38.6270, -90.1994),
    ("Indianapolis, Indiana, United States", 39.7684, -86.1581),
    ("Pittsburgh, Pennsylvania, United States", 40.4406, -79.9959),
    ("New York, New York, United States", 40.7128, -74.0060),
    ("Memphis, Tennessee, United States", 35.1495, -90.0490),
    ("Oklahoma City, Oklahoma, United States", 35.4676, -97.5164),
    ("Winnipeg, Manitoba, Canada", 49.8951, -97.1384),
    ("Calgary, Alberta, Canada", 51.0447, -114.0719),
    ("Toronto, Ontario, Canada", 43.6532, -79.3832),
    ("Honolulu, Hawaii, United States", 21.3069, -157.8583),
]


class FakeGeocoding:
    async def search(self, query: str, limit: int) -> list[Place]:
        q = normalize_query(query)
        hits = [c for c in _CITIES if q in c[0].lower()]
        return [
            Place(id=f"fake.{i}", label=label, position=LatLon(lat, lon))
            for i, (label, lat, lon) in enumerate(hits[:limit])
        ]
