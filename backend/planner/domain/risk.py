"""Risk classification (D-01 to D-04) and the continuous heatmap score (D-15)."""

import math
from collections.abc import Sequence

import numpy as np
import numpy.typing as npt

from .levels import (
    LOAD_WIND_NO_TRAVEL_ABOVE_LB,
    LOAD_WIND_SEVERE_ABOVE_LB,
    RAIN_BANDS,
    RAIN_NO_TRAVEL_ABOVE_IN_HR,
    SNOW_BANDS,
    SNOW_NO_TRAVEL_ABOVE_IN_HR,
    WIND_BANDS,
    WIND_NO_TRAVEL_MPH,
    Factor,
    Level,
    WindMetric,
)
from .models import RiskResult, WeatherSample

FloatArray = npt.NDArray[np.float64]

# Width of a band in score units. Just under 1 so floor(score) == level inside every band.
_BAND_SPAN = 0.999


def band(value: float, bands: Sequence[float]) -> Level:
    """Level from inclusive lower bounds of MODERATE, HIGH, SEVERE."""
    level = Level.LOW
    for i, edge in enumerate(bands, start=1):
        if value >= edge:
            level = Level(i)
    return level


def classify_wind(mph: float, load_lb: float) -> tuple[Level, bool]:
    """Returns (level, load_adjusted). Load rules only ever raise the wind level (D-03)."""
    if mph >= WIND_NO_TRAVEL_MPH:
        return Level.NO_TRAVEL, False
    base = band(mph, WIND_BANDS)
    if base is Level.SEVERE and load_lb > LOAD_WIND_NO_TRAVEL_ABOVE_LB:
        return Level.NO_TRAVEL, True
    if base is Level.HIGH and load_lb > LOAD_WIND_SEVERE_ABOVE_LB:
        return Level.SEVERE, True
    return base, False


def classify_rain(in_hr: float) -> Level:
    return Level.NO_TRAVEL if in_hr > RAIN_NO_TRAVEL_ABOVE_IN_HR else band(in_hr, RAIN_BANDS)


def classify_snow(in_hr: float) -> Level:
    return Level.NO_TRAVEL if in_hr > SNOW_NO_TRAVEL_ABOVE_IN_HR else band(in_hr, SNOW_BANDS)


def wind_input(ws: WeatherSample, metric: WindMetric) -> float | None:
    """D-04: gusts by default, sustained wind when configured."""
    return ws.gust_mph if metric == "gust" else ws.wind_mph


def classify_checkpoint(ws: WeatherSample, load_lb: float, metric: WindMetric) -> RiskResult:
    wind_v = wind_input(ws, metric)
    if wind_v is None or ws.rain_in_hr is None or ws.snow_in_hr is None:
        # Unknown weather is never safe weather (docs/03 §6).
        return RiskResult(
            wind=Level.UNKNOWN if wind_v is None else classify_wind(wind_v, load_lb)[0],
            rain=Level.UNKNOWN if ws.rain_in_hr is None else classify_rain(ws.rain_in_hr),
            snow=Level.UNKNOWN if ws.snow_in_hr is None else classify_snow(ws.snow_in_hr),
            overall=Level.UNKNOWN,
            dominant_factor=None,
            load_adjusted=False,
        )
    wind, adjusted = classify_wind(wind_v, load_lb)
    snow = classify_snow(ws.snow_in_hr)
    rain = classify_rain(ws.rain_in_hr)
    overall = max(wind, snow, rain)
    # D-02: ties prefer wind, then snow, then rain.
    factors: tuple[tuple[Factor, Level], ...] = (("wind", wind), ("snow", snow), ("rain", rain))
    dominant = next(name for name, lvl in factors if lvl == overall)
    return RiskResult(
        wind=wind,
        rain=rain,
        snow=snow,
        overall=overall,
        dominant_factor=dominant,
        load_adjusted=adjusted,
    )


# --- Continuous score for the heatmap (D-15, docs/03 §7.1) ---


def _piecewise(value: float, bands: Sequence[float], nt_edge: float, nt_inclusive: bool) -> float:
    """Maps a reading onto [0, 4] so that floor(score) == level, No Travel == 4.0."""
    if value > nt_edge or (nt_inclusive and value == nt_edge):
        return 4.0
    edges = (0.0, *bands, nt_edge)
    v = max(value, 0.0)
    k = int(band(v, bands))
    lo, hi = edges[k], edges[k + 1]
    return k + min((v - lo) / (hi - lo), 1.0) * _BAND_SPAN


def continuous_score(ws: WeatherSample, load_lb: float, metric: WindMetric) -> float | None:
    wind_v = wind_input(ws, metric)
    if wind_v is None or ws.rain_in_hr is None or ws.snow_in_hr is None:
        return None
    wind = _piecewise(wind_v, WIND_BANDS, WIND_NO_TRAVEL_MPH, nt_inclusive=True)
    load_level, _ = classify_wind(wind_v, load_lb)
    wind = max(wind, float(load_level))  # load rules lift the floor
    rain = _piecewise(ws.rain_in_hr, RAIN_BANDS, RAIN_NO_TRAVEL_ABOVE_IN_HR, nt_inclusive=False)
    snow = _piecewise(ws.snow_in_hr, SNOW_BANDS, SNOW_NO_TRAVEL_ABOVE_IN_HR, nt_inclusive=False)
    return max(wind, rain, snow)


def _piecewise_array(
    values: FloatArray, bands: Sequence[float], nt_edge: float, nt_inclusive: bool
) -> FloatArray:
    edges = np.array((0.0, *bands, nt_edge))
    v = np.maximum(values, 0.0)
    k = np.searchsorted(np.asarray(bands), v, side="right")  # count of bands <= v
    lo, hi = edges[k], edges[k + 1]
    score = k + np.minimum((v - lo) / (hi - lo), 1.0) * _BAND_SPAN
    no_travel = values >= nt_edge if nt_inclusive else values > nt_edge
    return np.where(no_travel, 4.0, score)


def continuous_score_array(
    wind_mph: FloatArray, rain_in_hr: FloatArray, snow_in_hr: FloatArray, load_lb: float
) -> FloatArray:
    """Vectorized `continuous_score`. `wind_mph` is the already-selected metric (D-04).
    NaN in any input gives NaN (no data)."""
    with np.errstate(invalid="ignore"):
        wind = _piecewise_array(wind_mph, WIND_BANDS, WIND_NO_TRAVEL_MPH, nt_inclusive=True)
        severe_band = (wind_mph >= WIND_BANDS[2]) & (wind_mph < WIND_NO_TRAVEL_MPH)
        high_band = (wind_mph >= WIND_BANDS[1]) & (wind_mph < WIND_BANDS[2])
        if load_lb > LOAD_WIND_NO_TRAVEL_ABOVE_LB:
            wind = np.where(severe_band, 4.0, wind)
        if load_lb > LOAD_WIND_SEVERE_ABOVE_LB:
            wind = np.where(high_band, np.maximum(wind, float(Level.SEVERE)), wind)
        rain = _piecewise_array(rain_in_hr, RAIN_BANDS, RAIN_NO_TRAVEL_ABOVE_IN_HR, False)
        snow = _piecewise_array(snow_in_hr, SNOW_BANDS, SNOW_NO_TRAVEL_ABOVE_IN_HR, False)
        score: FloatArray = np.maximum(np.maximum(wind, rain), snow)
    missing = np.isnan(wind_mph) | np.isnan(rain_in_hr) | np.isnan(snow_in_hr)
    return np.where(missing, math.nan, score)
