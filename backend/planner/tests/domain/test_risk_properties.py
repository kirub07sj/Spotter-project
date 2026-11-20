"""Property tests (docs/03 §7): monotonicity, overall >= components, and the heatmap
score agreeing with the discrete levels (D-15)."""

import math

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from planner.domain.levels import Level
from planner.domain.risk import (
    classify_checkpoint,
    classify_wind,
    continuous_score,
    continuous_score_array,
)
from planner.tests.domain.factories import sample

wind = st.floats(min_value=0, max_value=120, allow_nan=False)
rain = st.floats(min_value=0, max_value=3, allow_nan=False)
snow = st.floats(min_value=0, max_value=6, allow_nan=False)
load = st.integers(min_value=1, max_value=80_000)
bump = st.floats(min_value=0, max_value=50, allow_nan=False)


def overall(g: float, r: float, s: float, lb: int) -> Level:
    return classify_checkpoint(sample(gust=g, rain=r, snow=s), lb, "gust").overall


@given(wind, rain, snow, load, bump)
def test_raising_wind_never_lowers_overall(g: float, r: float, s: float, lb: int, d: float) -> None:
    assert overall(g + d, r, s, lb) >= overall(g, r, s, lb)


@given(wind, rain, snow, load, bump)
def test_raising_rain_never_lowers_overall(g: float, r: float, s: float, lb: int, d: float) -> None:
    assert overall(g, r + d / 10, s, lb) >= overall(g, r, s, lb)


@given(wind, rain, snow, load, bump)
def test_raising_snow_never_lowers_overall(g: float, r: float, s: float, lb: int, d: float) -> None:
    assert overall(g, r, s + d / 10, lb) >= overall(g, r, s, lb)


@given(wind, rain, snow, load, st.integers(min_value=0, max_value=80_000))
def test_raising_load_never_lowers_overall(g: float, r: float, s: float, lb: int, d: int) -> None:
    assert overall(g, r, s, lb + d) >= overall(g, r, s, lb)


@given(wind, rain, snow, load)
def test_overall_is_at_least_every_component(g: float, r: float, s: float, lb: int) -> None:
    res = classify_checkpoint(sample(gust=g, rain=r, snow=s), lb, "gust")
    assert res.overall >= max(res.wind, res.rain, res.snow)
    assert res.overall == max(res.wind, res.rain, res.snow)


@given(wind, load)
def test_load_rules_only_ever_raise_wind(g: float, lb: int) -> None:
    unloaded, _ = classify_wind(g, 0)
    loaded, adjusted = classify_wind(g, lb)
    assert loaded >= unloaded
    assert adjusted == (loaded != unloaded)


@given(wind, rain, snow, load)
def test_continuous_score_floor_equals_level(g: float, r: float, s: float, lb: int) -> None:
    ws = sample(gust=g, rain=r, snow=s)
    score = continuous_score(ws, lb, "gust")
    assert score is not None
    assert 0.0 <= score <= 4.0
    assert math.floor(score) == int(classify_checkpoint(ws, lb, "gust").overall)


def test_continuous_score_is_none_when_weather_missing() -> None:
    assert continuous_score(sample(rain=None), 0, "gust") is None


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_vectorized_score_matches_scalar_on_10k_random_inputs(seed: int) -> None:
    rng = np.random.default_rng(seed)
    n = 10_000
    # Mix uniform values with exact thresholds so the band edges get hit too.
    edges_w = np.array([0, 25, 35, 45, 55, 54.99, 44.99, 34.99, 24.99])
    edges_r = np.array([0, 0.1, 0.25, 0.5, 1.0, 1.0001, 0.0999])
    edges_s = np.array([0, 0.5, 1.0, 2.0, 3.0, 3.01, 0.49])
    w = np.where(rng.random(n) < 0.2, rng.choice(edges_w, n), rng.uniform(0, 80, n))
    r = np.where(rng.random(n) < 0.2, rng.choice(edges_r, n), rng.uniform(0, 1.5, n))
    s = np.where(rng.random(n) < 0.2, rng.choice(edges_s, n), rng.uniform(0, 4, n))
    w[rng.random(n) < 0.01] = np.nan  # missing values propagate as NaN
    lb = int(rng.integers(1, 80_001))
    vec = continuous_score_array(w, r, s, lb)
    for i in range(n):
        scalar = continuous_score(
            sample(
                gust=None if np.isnan(w[i]) else float(w[i]), rain=float(r[i]), snow=float(s[i])
            ),
            lb,
            "gust",
        )
        if scalar is None:
            assert np.isnan(vec[i])
        else:
            assert math.isclose(vec[i], scalar, abs_tol=1e-12), (i, w[i], r[i], s[i], lb)
