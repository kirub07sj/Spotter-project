from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from planner.domain.models import LatLon
from planner.domain.scenarios import (
    ScenarioAnchor,
    apply_delta,
    scenario_delta,
    scenario_fields,
)
from planner.tests.domain.factories import sample

T0 = datetime(2026, 11, 20, 13, 0, tzinfo=UTC)
ANCHOR = ScenarioAnchor(center=LatLon(41.0, -108.0), start=T0)


def test_winter_storm_peaks_at_the_anchor_at_start() -> None:
    d = scenario_delta("winter_storm", ANCHOR, ANCHOR.center, T0)
    assert d.snow_in_hr == pytest.approx(2.5)
    assert d.gust_mph == pytest.approx(50.0)
    assert d.rain_in_hr == 0.0


def test_storm_moves_east_at_30_kmh() -> None:
    later = T0 + timedelta(hours=10)
    # 300 km east of the anchor, at the same latitude.
    east = LatLon(41.0, -108.0 + 300 / (111.195 * np.cos(np.radians(41.0))))
    assert scenario_delta("winter_storm", ANCHOR, east, later).snow_in_hr == pytest.approx(
        2.5, rel=1e-3
    )
    assert scenario_delta("winter_storm", ANCHOR, ANCHOR.center, later).snow_in_hr < 0.05


def test_fades_with_distance() -> None:
    far = LatLon(45.0, -100.0)
    assert scenario_delta("winter_storm", ANCHOR, far, T0).gust_mph < 1e-6


def test_high_wind_has_no_precipitation() -> None:
    d = scenario_delta("high_wind", ANCHOR, ANCHOR.center, T0)
    assert d.gust_mph == pytest.approx(42.0) and d.snow_in_hr == 0.0


def test_vectorized_matches_scalar() -> None:
    lats = np.array([40.5, 41.0, 41.3])
    lons = np.array([-108.5, -108.0, -107.2])
    hours = np.array([0.0, 5.0, 12.0])
    _, gust, _, snow = scenario_fields("winter_storm", ANCHOR, lats, lons, hours)
    for i in range(3):
        d = scenario_delta(
            "winter_storm", ANCHOR, LatLon(lats[i], lons[i]), T0 + timedelta(hours=hours[i])
        )
        assert gust[i] == pytest.approx(d.gust_mph) and snow[i] == pytest.approx(d.snow_in_hr)


def test_apply_delta_adds_and_keeps_missing_missing() -> None:
    d = scenario_delta("winter_storm", ANCHOR, ANCHOR.center, T0)
    out = apply_delta(sample(gust=10, snow=None, rain=0.05), d)
    assert out.gust_mph == pytest.approx(60.0)
    assert out.snow_in_hr is None
    assert out.rain_in_hr == pytest.approx(0.05)
