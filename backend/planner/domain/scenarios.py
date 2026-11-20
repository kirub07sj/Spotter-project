"""Simulated weather overlays for demos and tests (D-20, docs/03 §12).

A scenario is a pure function of (lat, lon, t) that is added to the real forecast before
classification. Checkpoints and the heatmap both call it, so they stay consistent."""

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import numpy as np
import numpy.typing as npt

from .geo import EARTH_RADIUS_M
from .models import LatLon, WeatherSample

ScenarioName = Literal["winter_storm", "high_wind"]
SCENARIOS: tuple[ScenarioName, ...] = ("winter_storm", "high_wind")
FloatArray = npt.NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class StormSpec:
    radius_km: float
    peak_gust_mph: float
    peak_wind_mph: float
    peak_snow_in_hr: float
    peak_rain_in_hr: float
    speed_kmh: float
    heading_deg: float  # direction of travel, clockwise from north
    along_route_fraction: float  # where on route A the storm starts


STORMS: dict[ScenarioName, StormSpec] = {
    # Blob on route A's midpoint, moving east at 30 km/h (docs/03 §12).
    "winter_storm": StormSpec(120, 50, 30, 2.5, 0.0, 30, 90, 0.5),
    # Broad wind ridge with no precipitation, moving north-east; shows the load rules.
    "high_wind": StormSpec(220, 42, 25, 0.0, 0.0, 40, 45, 0.35),
}


@dataclass(frozen=True, slots=True)
class ScenarioAnchor:
    """Where and when the storm starts: a point on route A and the departure hour."""

    center: LatLon
    start: datetime


@dataclass(frozen=True, slots=True)
class WeatherDelta:
    wind_mph: float
    gust_mph: float
    rain_in_hr: float
    snow_in_hr: float


def _intensity(
    spec: StormSpec, anchor: ScenarioAnchor, lat: FloatArray, lon: FloatArray, hours: FloatArray
) -> FloatArray:
    travelled_m = spec.speed_kmh * 1000.0 * hours
    heading = math.radians(spec.heading_deg)
    k = EARTH_RADIUS_M * math.pi / 180.0
    cos_lat0 = math.cos(math.radians(anchor.center.lat))
    center_y = anchor.center.lat * k + travelled_m * math.cos(heading)
    center_x = anchor.center.lon * k * cos_lat0 + travelled_m * math.sin(heading)
    dx = lon * k * cos_lat0 - center_x
    dy = lat * k - center_y
    radius_m = spec.radius_km * 1000.0
    result: FloatArray = np.exp(-(dx * dx + dy * dy) / (radius_m * radius_m))
    return result


def scenario_fields(
    name: ScenarioName,
    anchor: ScenarioAnchor,
    lat: FloatArray,
    lon: FloatArray,
    hours_since_start: FloatArray,
) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
    """Vectorized deltas (wind, gust, rain, snow) for broadcastable lat/lon/hour arrays."""
    spec = STORMS[name]
    f = _intensity(spec, anchor, lat, lon, hours_since_start)
    return (
        f * spec.peak_wind_mph,
        f * spec.peak_gust_mph,
        f * spec.peak_rain_in_hr,
        f * spec.peak_snow_in_hr,
    )


def scenario_delta(
    name: ScenarioName, anchor: ScenarioAnchor, position: LatLon, t: datetime
) -> WeatherDelta:
    hours = np.array([(t - anchor.start).total_seconds() / 3600.0])
    wind, gust, rain, snow = scenario_fields(
        name, anchor, np.array([position.lat]), np.array([position.lon]), hours
    )
    return WeatherDelta(float(wind[0]), float(gust[0]), float(rain[0]), float(snow[0]))


def apply_delta(ws: WeatherSample, delta: WeatherDelta) -> WeatherSample:
    """Missing stays missing: a scenario never invents data where the forecast has none."""

    def add(value: float | None, extra: float) -> float | None:
        return None if value is None else value + extra

    return WeatherSample(
        wind_mph=add(ws.wind_mph, delta.wind_mph),
        gust_mph=add(ws.gust_mph, delta.gust_mph),
        rain_in_hr=add(ws.rain_in_hr, delta.rain_in_hr),
        snow_in_hr=add(ws.snow_in_hr, delta.snow_in_hr),
        forecast_hour=ws.forecast_hour,
    )
