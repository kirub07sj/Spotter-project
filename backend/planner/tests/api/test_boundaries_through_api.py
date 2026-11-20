"""QA R3 (docs/06 §4): the boundary table gives the expected levels through the API, not
only in the domain. One 100-mile route whose every checkpoint has the same weather."""

import pytest
from rest_framework.test import APIClient

from planner.domain.levels import Level
from planner.providers.registry import use_providers
from planner.tests.api.conftest import plan_body
from planner.tests.domain.test_risk_boundaries import RAIN_CASES, SNOW_CASES, WIND_CASES
from planner.tests.golden import GoldenRoute, GoldenScenario, W
from planner.tests.golden_providers import golden_providers

CASES = [
    *[(W(gust=mph), load, lvl, adjusted) for mph, load, lvl, adjusted in WIND_CASES],
    *[(W(gust=0.0, rain=rate), 1, lvl, False) for rate, lvl in RAIN_CASES],
    *[(W(gust=0.0, snow=rate), 1, lvl, False) for rate, lvl in SNOW_CASES],
]


@pytest.mark.parametrize(("weather", "load", "expected", "adjusted"), CASES)
def test_boundary_levels_through_post_plans(
    client: APIClient, weather: W, load: int, expected: Level, adjusted: bool
) -> None:
    scenario = GoldenScenario(
        routes={"A": GoldenRoute(100, (weather,) * 5)},
        load_lb=max(load, 1),
        expected_winner="A",
        expected_status="",
        expected_order=["A"],
        expected_reasons=(),
    )
    with use_providers(golden_providers(scenario)):
        r = client.post("/api/v1/plans", plan_body(load_weight_lb=max(load, 1)), format="json")
    assert r.status_code == 200, r.content
    (route,) = r.json()["routes"]
    for cp in route["checkpoints"]:
        assert cp["levels"]["overall"] == expected.name
        assert cp["load_adjusted"] is adjusted
    assert route["stats"]["max_level"] == expected.name
