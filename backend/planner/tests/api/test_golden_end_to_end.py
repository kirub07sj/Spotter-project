"""The six golden scenarios through POST /api/v1/plans: routing -> sampling -> weather
lookup -> classification -> attribution -> ranking -> JSON (docs/03 §9)."""

import pytest
from rest_framework.test import APIClient

from planner.providers.registry import use_providers
from planner.tests.api.conftest import plan_body
from planner.tests.golden import GOLDEN_SCENARIOS
from planner.tests.golden_providers import golden_providers


@pytest.mark.parametrize("name", sorted(GOLDEN_SCENARIOS))
def test_golden_scenario_end_to_end(client: APIClient, name: str) -> None:
    scenario = GOLDEN_SCENARIOS[name]
    with use_providers(golden_providers(scenario)):
        response = client.post(
            "/api/v1/plans", plan_body(load_weight_lb=scenario.load_lb), format="json"
        )
    assert response.status_code == 200, response.content
    plan = response.json()
    rec = plan["recommendation"]
    assert rec["route_id"] == scenario.expected_winner
    assert rec["status"] == scenario.expected_status
    assert tuple(rec["reasons"]) == scenario.expected_reasons
    by_rank = sorted(plan["routes"], key=lambda r: r["rank"])
    assert [r["id"] for r in by_rank] == scenario.expected_order
    assert [r["id"] for r in plan["routes"] if r["recommended"]] == [scenario.expected_winner]
    for route in plan["routes"]:
        assert [cp["mile"] for cp in route["checkpoints"]] == [0.0, 25.0, 50.0, 75.0, 100.0]
        assert [cp["owned_mi"] for cp in route["checkpoints"]] == [12.5, 25.0, 25.0, 25.0, 12.5]
        assert route["duration_s"] == scenario.routes[route["id"]].minutes * 60
    assert plan["warnings"] == []


def test_load_rule_flip_is_visible_on_the_checkpoint(client: APIClient) -> None:
    scenario = GOLDEN_SCENARIOS["load_flip_45k"]
    with use_providers(golden_providers(scenario)):
        plan = client.post("/api/v1/plans", plan_body(load_weight_lb=45_000), format="json").json()
    route_a = next(r for r in plan["routes"] if r["id"] == "A")
    cp = route_a["checkpoints"][2]
    assert cp["levels"] == {"wind": "SEVERE", "rain": "LOW", "snow": "LOW", "overall": "SEVERE"}
    assert cp["load_adjusted"] is True and cp["dominant_factor"] == "wind"
    assert route_a["stats"]["miles_by_level"]["SEVERE"] == 25.0
    assert [s["level"] for s in route_a["risk_segments"]] == ["LOW", "SEVERE", "LOW"]
    assert [(s["from_mi"], s["to_mi"]) for s in route_a["risk_segments"]] == [
        (0.0, 37.5),
        (37.5, 62.5),
        (62.5, 100.0),
    ]


def test_no_safe_route_still_highlights_least_bad(client: APIClient) -> None:
    with use_providers(golden_providers(GOLDEN_SCENARIOS["no_safe_route"])):
        plan = client.post("/api/v1/plans", plan_body(), format="json").json()
    assert plan["recommendation"]["status"] == "NO_SAFE_ROUTE"
    a = next(r for r in plan["routes"] if r["id"] == "A")
    assert a["recommended"] and a["stats"]["max_level"] == "NO_TRAVEL"
    assert any(s["level"] == "NO_TRAVEL" for s in a["risk_segments"])
