"""Providers that reproduce a golden scenario end to end: three parallel 100-mile routes
(A at 40.0N, B at 40.5N, C at 41.0N, heading east) and weather scripted per checkpoint."""

import math
from collections.abc import Sequence
from datetime import datetime

from planner.domain.models import HourlySeries, LatLon, Place, RouteGeometry
from planner.domain.units import M_PER_MI
from planner.providers.fakes import FakeGeocoding
from planner.providers.registry import Providers
from planner.tests.golden import CALM, GoldenScenario, W

ROUTE_LATS = {"A": 40.0, "B": 40.5, "C": 41.0}
LON0 = -105.0
N_SEGMENTS = 100  # one segment per mile


def lon_step(lat: float) -> float:
    """Longitude step whose haversine length along the parallel is exactly one mile."""
    r = 6_371_008.8
    return math.degrees(2 * math.asin(math.sin(M_PER_MI / (2 * r)) / math.cos(math.radians(lat))))


class GoldenRouting:
    def __init__(self, scenario: GoldenScenario) -> None:
        self.scenario = scenario

    async def route(
        self,
        origin: LatLon,
        destination: LatLon,
        *,
        via: LatLon | None = None,
        alternatives: bool = True,
        load_lb: float = 0.0,
    ) -> list[RouteGeometry]:
        out = []
        for rid, gr in self.scenario.routes.items():
            lat, step = ROUTE_LATS[rid], lon_step(ROUTE_LATS[rid])
            coords = tuple(LatLon(lat, LON0 + i * step) for i in range(N_SEGMENTS + 1))
            seg_s = gr.minutes * 60.0 / N_SEGMENTS
            out.append(
                RouteGeometry(
                    coords, (M_PER_MI,) * N_SEGMENTS, (seg_s,) * N_SEGMENTS, f"Golden {rid}"
                )
            )
        return out


class ScriptedWeather:
    def __init__(self, scenario: GoldenScenario) -> None:
        self.scenario = scenario

    def weather_at(self, p: LatLon) -> W:
        rid = min(ROUTE_LATS, key=lambda r: abs(ROUTE_LATS[r] - p.lat))
        mile = (p.lon - LON0) / lon_step(ROUTE_LATS[rid])
        index = round(mile / 25)
        assert abs(mile - index * 25) < 0.01, "checkpoint off the 25-mile grid"
        return self.scenario.routes[rid].weather[index] if rid in self.scenario.routes else CALM

    async def hourly(
        self, points: Sequence[LatLon], start: datetime, end: datetime
    ) -> list[HourlySeries]:
        hours = int((end - start).total_seconds() // 3600) + 1
        times = tuple(int(start.timestamp()) + 3600 * i for i in range(hours))
        out = []
        for p in points:
            w = self.weather_at(p)
            out.append(
                HourlySeries(
                    times=times,
                    wind_mph=(w.gust * 0.7,) * hours,
                    gust_mph=(w.gust,) * hours,
                    rain_in_hr=(w.rain,) * hours,
                    snow_in_hr=(w.snow,) * hours,
                )
            )
        return out


class NoGeocoding(FakeGeocoding):
    async def search(self, query: str, limit: int) -> list[Place]:
        return []


def golden_providers(scenario: GoldenScenario) -> Providers:
    return Providers(GoldenRouting(scenario), FakeGeocoding(), ScriptedWeather(scenario), "fake")
