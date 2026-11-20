"""Frozen domain models. Units: miles, seconds, mph, in/hr, lb, UTC-aware datetime."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from .levels import Factor, Level


@dataclass(frozen=True, slots=True)
class LatLon:
    lat: float
    lon: float


@dataclass(frozen=True, slots=True)
class Place:
    id: str
    label: str
    position: LatLon


@dataclass(frozen=True, slots=True)
class RouteGeometry:
    coords: tuple[LatLon, ...]  # full resolution
    seg_dist_m: tuple[float, ...]  # len(coords) - 1
    seg_dur_s: tuple[float, ...]  # len(coords) - 1, provider (car) durations
    summary: str = ""

    @property
    def distance_m(self) -> float:
        return sum(self.seg_dist_m)

    @property
    def duration_s(self) -> float:
        return sum(self.seg_dur_s)


@dataclass(frozen=True, slots=True)
class Checkpoint:
    index: int
    mile: float
    position: LatLon
    eta: datetime


@dataclass(frozen=True, slots=True)
class HourlySeries:
    """One location's hourly forecast, already in domain units. Each value at `times[i]`
    covers the preceding hour (D-08). `None` marks a missing value."""

    times: tuple[int, ...]  # unix seconds, hourly
    wind_mph: tuple[float | None, ...]
    gust_mph: tuple[float | None, ...]
    rain_in_hr: tuple[float | None, ...]  # rain + showers (D-05)
    snow_in_hr: tuple[float | None, ...]  # snowfall (D-05)


@dataclass(frozen=True, slots=True)
class WeatherSample:
    wind_mph: float | None
    gust_mph: float | None
    rain_in_hr: float | None
    snow_in_hr: float | None
    forecast_hour: datetime

    @property
    def is_complete(self) -> bool:
        return None not in (self.wind_mph, self.gust_mph, self.rain_in_hr, self.snow_in_hr)


@dataclass(frozen=True, slots=True)
class RiskResult:
    wind: Level
    rain: Level
    snow: Level
    overall: Level
    dominant_factor: Factor | None
    load_adjusted: bool


@dataclass(frozen=True, slots=True)
class RouteStats:
    miles_by_level: Mapping[Level, float]  # known levels only
    avg_risk: float  # D-10, 0.00 to 4.00
    max_level: Level
    unknown_mi: float


@dataclass(frozen=True, slots=True)
class RiskRun:
    from_mi: float
    to_mi: float
    level: Level
