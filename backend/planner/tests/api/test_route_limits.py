from dataclasses import replace

import pytest
from rest_framework.test import APIClient

from planner.api.serializers import PlanRequestSerializer
from planner.domain.models import LatLon, RouteGeometry
from planner.domain.units import mi_to_m
from planner.providers.fakes import FakeGeocoding, FakeRouting, FakeWeather
from planner.providers.registry import Providers, use_providers
from planner.tests.api.conftest import next_hour, plan_body


def test_distinct_points_under_a_tenth_mile_are_valid() -> None:
    now = next_hour()
    request = PlanRequestSerializer(
        data=plan_body(destination={"lat": 39.7393, "lon": -104.9903}), context={"now": now}
    )
    assert request.is_valid(), request.errors


class LongAlternativeRouting(FakeRouting):
    def __init__(self, long_via: bool) -> None:
        self.long_via = long_via

    async def route(
        self,
        origin: LatLon,
        destination: LatLon,
        *,
        via: LatLon | None = None,
        alternatives: bool = True,
        load_lb: float = 0.0,
    ) -> list[RouteGeometry]:
        routes = await super().route(
            origin, destination, via=via, alternatives=alternatives, load_lb=load_lb
        )
        if via is None and self.long_via:
            return routes[:1]
        return [
            replace(
                route,
                seg_dist_m=tuple(mi_to_m(3100) / len(route.seg_dist_m) for _ in route.seg_dist_m),
            )
            if via is not None or i > 0
            else route
            for i, route in enumerate(routes)
        ]


@pytest.mark.parametrize("long_via", [False, True])
def test_overlong_alternatives_are_excluded(client: APIClient, long_via: bool) -> None:
    providers = Providers(LongAlternativeRouting(long_via), FakeGeocoding(), FakeWeather(), "fake")
    with use_providers(providers):
        response = client.post("/api/v1/plans", plan_body(), format="json")
    assert response.status_code == 200
    plan = response.json()
    assert len(plan["routes"]) == 1
    assert all(route["distance_mi"] <= 3000 for route in plan["routes"])
    assert any(w["code"] == "ONLY_N_DISTINCT_ROUTES" for w in plan["warnings"])
