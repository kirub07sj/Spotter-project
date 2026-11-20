"""corridor -> grid -> weather -> score -> encode (docs/02 §1, docs/03 §10)."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np

from planner.domain.geo import cumulative, segment_lengths_m
from planner.domain.heatmap import Grid, build_grid, encode_mask, encode_scores
from planner.domain.levels import WindMetric
from planner.domain.models import HourlySeries, LatLon
from planner.domain.risk import FloatArray, continuous_score_array
from planner.domain.scenarios import ScenarioName, scenario_fields
from planner.domain.weather_lookup import bucket_time
from planner.providers.registry import Providers

from .plan_service import scenario_anchor
from .timing import Timings

log = logging.getLogger(__name__)
HOURS = 49  # departure + 0h .. +48h (D-14)


@dataclass(frozen=True, slots=True)
class HeatmapRequest:
    routes: list[list[LatLon]]
    departure: datetime
    load_lb: int
    scenario: ScenarioName | None


@dataclass(frozen=True, slots=True)
class HeatmapConfig:
    wind_metric: WindMetric
    corridor_km: float
    max_points: int


@dataclass(frozen=True, slots=True)
class Heatmap:
    grid: Grid
    hours: list[datetime]
    mask: bytes
    scores: bytes
    masked_points: int


def _stack(
    series: Sequence[HourlySeries], start: datetime, metric: WindMetric
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """(points, HOURS) arrays aligned to start + k hours; missing -> NaN."""
    shape = (len(series), HOURS)
    wind, rain, snow = np.full(shape, np.nan), np.full(shape, np.nan), np.full(shape, np.nan)
    t0 = int(start.timestamp())
    for i, s in enumerate(series):
        winds = s.gust_mph if metric == "gust" else s.wind_mph
        for j, t in enumerate(s.times):
            k = (t - t0) // 3600
            if 0 <= k < HOURS and (t - t0) % 3600 == 0:
                wind[i, k] = np.nan if winds[j] is None else winds[j]
                rain[i, k] = np.nan if s.rain_in_hr[j] is None else s.rain_in_hr[j]
                snow[i, k] = np.nan if s.snow_in_hr[j] is None else s.snow_in_hr[j]
    return wind, rain, snow


async def create_heatmap(
    req: HeatmapRequest, providers: Providers, config: HeatmapConfig, timings: Timings
) -> Heatmap:
    with timings.measure("compute"):
        grid, mask = build_grid(req.routes, config.corridor_km, config.max_points)
        lat, lon = grid.cell_centers()
        rows_idx, cols_idx = np.nonzero(mask)
        points = [
            LatLon(float(lat[r, c]), float(lon[r, c]))
            for r, c in zip(rows_idx, cols_idx, strict=True)
        ]
        # D-08/D-14: each departure-relative frame uses its ending hourly bucket.
        start = bucket_time(req.departure)
    with timings.measure("weather"):
        series = await providers.weather.hourly(points, start, start + timedelta(hours=HOURS - 1))
    with timings.measure("compute"):
        wind, rain, snow = _stack(series, start, config.wind_metric)
        if req.scenario:
            route_a = req.routes[0]
            anchor = scenario_anchor(
                req.scenario, route_a, cumulative(segment_lengths_m(route_a)), req.departure
            )
            p_lat = lat[mask][:, np.newaxis]
            p_lon = lon[mask][:, np.newaxis]
            offset_h = (start - anchor.start).total_seconds() / 3600
            hours = np.arange(HOURS, dtype=np.float64)[np.newaxis, :] + offset_h
            d_wind, d_gust, d_rain, d_snow = scenario_fields(
                req.scenario, anchor, p_lat, p_lon, hours
            )
            wind = wind + (d_gust if config.wind_metric == "gust" else d_wind)
            rain, snow = rain + d_rain, snow + d_snow
        point_scores = continuous_score_array(wind, rain, snow, req.load_lb)  # (points, HOURS)
        full = np.full((HOURS, grid.rows, grid.cols), np.nan)
        full[:, rows_idx, cols_idx] = point_scores.T
        heatmap = Heatmap(
            grid=grid,
            hours=[req.departure + timedelta(hours=k) for k in range(HOURS)],
            mask=encode_mask(mask),
            scores=encode_scores(full, mask),
            masked_points=len(points),
        )
    log.info("heatmap created", extra={"rows": grid.rows, "cols": grid.cols, "points": len(points)})
    return heatmap
