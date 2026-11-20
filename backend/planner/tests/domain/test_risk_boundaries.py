"""Table-driven threshold edges (docs/03 §7, D-01, D-03). Values are derived from
`levels.py` so a threshold change shows up here automatically; `test_thresholds_match_spec`
is the one deliberate lock that forces the spec, decisions log and tests to change together."""

import pytest

from planner.domain import levels as L
from planner.domain.levels import Level
from planner.domain.models import WeatherSample
from planner.domain.risk import (
    classify_checkpoint,
    classify_rain,
    classify_snow,
    classify_wind,
)
from planner.tests.domain.factories import sample

LOAD_NT = L.LOAD_WIND_NO_TRAVEL_ABOVE_LB
LOAD_SEV = L.LOAD_WIND_SEVERE_ABOVE_LB


def test_thresholds_match_spec() -> None:
    # Spec lock (01-SPEC D-01, D-03). Changing any number here requires a spec change.
    assert (L.WIND_MODERATE_MPH, L.WIND_HIGH_MPH, L.WIND_SEVERE_MPH) == (25.0, 35.0, 45.0)
    assert L.WIND_NO_TRAVEL_MPH == 55.0
    assert (L.RAIN_MODERATE_IN_HR, L.RAIN_HIGH_IN_HR, L.RAIN_SEVERE_IN_HR) == (0.10, 0.25, 0.50)
    assert L.RAIN_NO_TRAVEL_ABOVE_IN_HR == 1.00
    assert (L.SNOW_MODERATE_IN_HR, L.SNOW_HIGH_IN_HR, L.SNOW_SEVERE_IN_HR) == (0.5, 1.0, 2.0)
    assert L.SNOW_NO_TRAVEL_ABOVE_IN_HR == 3.0
    assert (LOAD_NT, LOAD_SEV) == (30_000, 40_000)


WIND_CASES = [
    # (mph, load_lb, expected level, load_adjusted)
    (L.WIND_MODERATE_MPH - 0.01, 0, Level.LOW, False),  # 24.99
    (L.WIND_MODERATE_MPH, 0, Level.MODERATE, False),  # 25.0
    (L.WIND_HIGH_MPH - 0.01, 0, Level.MODERATE, False),  # 34.99
    (L.WIND_HIGH_MPH, 0, Level.HIGH, False),  # 35.0
    (L.WIND_HIGH_MPH, LOAD_SEV, Level.HIGH, False),  # 35.0 @ 40,000: not > 40k
    (L.WIND_HIGH_MPH, LOAD_SEV + 1, Level.SEVERE, True),  # 35.0 @ 40,001
    (L.WIND_SEVERE_MPH - 0.01, LOAD_SEV, Level.HIGH, False),  # 44.99 @ 40,000
    (L.WIND_SEVERE_MPH - 0.01, 45_000, Level.SEVERE, True),  # 44.99 @ 45,000
    (L.WIND_SEVERE_MPH, 0, Level.SEVERE, False),  # 45.0
    (L.WIND_SEVERE_MPH, LOAD_NT, Level.SEVERE, False),  # 45.0 @ 30,000: not > 30k
    (L.WIND_SEVERE_MPH, LOAD_NT + 1, Level.NO_TRAVEL, True),  # 45.0 @ 30,001
    (L.WIND_NO_TRAVEL_MPH - 0.01, 0, Level.SEVERE, False),  # 54.99
    (L.WIND_NO_TRAVEL_MPH - 0.01, LOAD_NT + 1, Level.NO_TRAVEL, True),  # 54.99 @ 30,001
    (L.WIND_NO_TRAVEL_MPH, 0, Level.NO_TRAVEL, False),  # 55.0, any load
    (L.WIND_NO_TRAVEL_MPH, 80_000, Level.NO_TRAVEL, False),  # load rule not the cause
    # The 35-44 load rule must not touch the 45-54 band or below 35 mph.
    (L.WIND_HIGH_MPH - 0.01, 80_000, Level.MODERATE, False),
    (L.WIND_SEVERE_MPH, LOAD_SEV + 1, Level.NO_TRAVEL, True),
    (0.0, 80_000, Level.LOW, False),
]


@pytest.mark.parametrize(("mph", "load", "expected", "adjusted"), WIND_CASES)
def test_wind_bands_and_load_rules(mph: float, load: int, expected: Level, adjusted: bool) -> None:
    assert classify_wind(mph, load) == (expected, adjusted)


RAIN_CASES = [
    (0.0, Level.LOW),
    (L.RAIN_MODERATE_IN_HR - 0.0001, Level.LOW),  # 0.0999
    (L.RAIN_MODERATE_IN_HR, Level.MODERATE),  # 0.10
    (L.RAIN_HIGH_IN_HR - 0.0001, Level.MODERATE),  # 0.2499
    (L.RAIN_HIGH_IN_HR, Level.HIGH),  # 0.25
    (L.RAIN_SEVERE_IN_HR - 0.0001, Level.HIGH),  # 0.4999
    (L.RAIN_SEVERE_IN_HR, Level.SEVERE),  # 0.50
    (L.RAIN_NO_TRAVEL_ABOVE_IN_HR, Level.SEVERE),  # 1.00 is still Severe (strict >)
    (L.RAIN_NO_TRAVEL_ABOVE_IN_HR + 0.0001, Level.NO_TRAVEL),  # 1.0001
]


@pytest.mark.parametrize(("rate", "expected"), RAIN_CASES)
def test_rain_bands(rate: float, expected: Level) -> None:
    assert classify_rain(rate) is expected


SNOW_CASES = [
    (0.0, Level.LOW),
    (L.SNOW_MODERATE_IN_HR - 0.01, Level.LOW),  # 0.49
    (L.SNOW_MODERATE_IN_HR, Level.MODERATE),  # 0.5
    (L.SNOW_HIGH_IN_HR - 0.01, Level.MODERATE),  # 0.99
    (L.SNOW_HIGH_IN_HR, Level.HIGH),  # 1.0
    (L.SNOW_SEVERE_IN_HR - 0.01, Level.HIGH),  # 1.99
    (L.SNOW_SEVERE_IN_HR, Level.SEVERE),  # 2.0
    (L.SNOW_NO_TRAVEL_ABOVE_IN_HR, Level.SEVERE),  # 3.0 is still Severe (strict >)
    (L.SNOW_NO_TRAVEL_ABOVE_IN_HR + 0.01, Level.NO_TRAVEL),  # 3.01
]


@pytest.mark.parametrize(("rate", "expected"), SNOW_CASES)
def test_snow_bands(rate: float, expected: Level) -> None:
    assert classify_snow(rate) is expected


def test_load_rules_change_only_wind() -> None:
    # D-03: heavy load with heavy rain/snow but calm wind stays as the weather says.
    result = classify_checkpoint(sample(gust=10, rain=0.3, snow=1.5), 80_000, "gust")
    assert (result.wind, result.rain, result.snow) == (Level.LOW, Level.HIGH, Level.HIGH)
    assert result.overall is Level.HIGH
    assert result.load_adjusted is False


def test_overall_is_max_and_records_dominant_factor() -> None:
    result = classify_checkpoint(sample(gust=40, rain=0.6, snow=0.7), 0, "gust")
    assert (result.wind, result.rain, result.snow) == (Level.HIGH, Level.SEVERE, Level.MODERATE)
    assert result.overall is Level.SEVERE
    assert result.dominant_factor == "rain"


@pytest.mark.parametrize(
    ("ws", "dominant"),
    [
        (sample(gust=40, rain=0.3, snow=1.5), "wind"),  # all HIGH: wind first
        (sample(gust=10, rain=0.3, snow=1.5), "snow"),  # snow beats rain on a tie
        (sample(gust=10, rain=0.0, snow=0.0), "wind"),  # all LOW: wind
    ],
)
def test_dominant_factor_tie_order_wind_snow_rain(ws: WeatherSample, dominant: str) -> None:
    assert classify_checkpoint(ws, 0, "gust").dominant_factor == dominant


def test_load_adjusted_flag_is_reported_on_checkpoint() -> None:
    result = classify_checkpoint(sample(gust=38), 42_000, "gust")
    assert result.wind is Level.SEVERE
    assert result.load_adjusted is True
    assert result.dominant_factor == "wind"


def test_wind_metric_selects_gust_or_sustained() -> None:
    ws = sample(wind=20, gust=48)  # D-04: gust is the default classification input
    assert classify_checkpoint(ws, 0, "gust").wind is Level.SEVERE
    assert classify_checkpoint(ws, 0, "sustained").wind is Level.LOW


@pytest.mark.parametrize("missing", ["wind", "gust", "rain", "snow"])
def test_missing_weather_is_unknown_never_low(missing: str) -> None:
    values: dict[str, float | None] = {"wind": 5.0, "gust": 8.0, "rain": 0.0, "snow": 0.0}
    values[missing] = None
    ws = sample(**values)
    result = classify_checkpoint(ws, 0, "gust" if missing != "wind" else "sustained")
    assert result.overall is Level.UNKNOWN
    assert result.dominant_factor is None


def test_missing_display_only_field_does_not_block_classification() -> None:
    # Sustained wind is display-only when classifying by gust (D-04).
    result = classify_checkpoint(sample(wind=None, gust=30), 0, "gust")
    assert result.overall is Level.MODERATE
