from datetime import UTC, datetime, timedelta

import polyline
import pytest
from rest_framework.test import APIClient

from planner.api.serializers import PlanResponseSerializer, ProblemSerializer
from planner.domain.errors import ProviderUnavailableError
from planner.providers.fakes import FakeGeocoding, FakeRouting, FakeWeather
from planner.providers.registry import Providers, use_providers
from planner.tests.api.conftest import next_hour, plan_body

pytestmark = pytest.mark.usefixtures("fake_providers")


def post(client: APIClient, query: str = "", **overrides: object) -> dict:
    response = client.post(f"/api/v1/plans{query}", plan_body(**overrides), format="json")
    return {"status": response.status_code, "body": response.json(), "headers": response}


def test_response_matches_the_schema(client: APIClient) -> None:
    r = post(client)
    assert r["status"] == 200
    assert PlanResponseSerializer(data=r["body"]).is_valid(raise_exception=True)


def test_three_routes_with_via_fallback_and_full_contract(client: APIClient) -> None:
    plan = post(client)["body"]
    routes = plan["routes"]
    assert [r["id"] for r in routes] == ["A", "B", "C"]
    durations = [r["duration_s"] for r in routes]
    assert durations == sorted(durations)  # ids by ascending duration
    assert {r["source"] for r in routes} == {"provider", "via"}  # fake gives 2, via adds 1
    assert sorted(r["rank"] for r in routes) == [1, 2, 3]
    for r in routes:
        coords = polyline.decode(r["geometry"], 6)
        assert len(coords) == len(r["cum_time_s"]) <= 2000
        assert r["cum_time_s"][0] == 0.0
        assert r["cum_time_s"][-1] == pytest.approx(r["duration_s"], abs=1)
        cps = r["checkpoints"]
        etas = [datetime.fromisoformat(cp["eta"]) for cp in cps]
        assert etas == sorted(etas) and etas[0].tzinfo is not None
        assert sum(cp["owned_mi"] for cp in cps) == pytest.approx(r["distance_mi"], abs=0.1)
        assert r["risk_segments"][0]["from_mi"] == 0.0
        assert r["risk_segments"][-1]["to_mi"] == pytest.approx(r["distance_mi"], abs=0.05)
        assert sum(r["stats"]["miles_by_level"].values()) == pytest.approx(
            r["distance_mi"], abs=0.3
        )
    assert plan["assumptions"]["wind_metric"] == "gust"
    assert plan["assumptions"]["truck_max_speed_mph"] == 65.0
    assert plan["assumptions"]["hos_breaks"] is False


def test_speed_cap_applies_to_durations(client: APIClient) -> None:
    plan = post(client)["body"]
    for r in plan["routes"]:
        assert r["distance_mi"] / (r["duration_s"] / 3600) <= 65.0 + 1e-6


def test_server_timing_header(client: APIClient) -> None:
    header = post(client)["headers"]["Server-Timing"]
    for stage in ("routing", "weather", "compute", "serialize"):
        assert f"{stage};dur=" in header


def test_interval_changes_checkpoint_count(client: APIClient) -> None:
    counts = {
        n: len(post(client, sample_interval_mi=n)["body"]["routes"][0]["checkpoints"])
        for n in (10, 25, 50)
    }
    assert counts[10] > counts[25] > counts[50] >= 2


def test_scenario_adds_badge_warning_and_raises_risk(client: APIClient) -> None:
    calm = post(client)["body"]
    storm = post(client, "?scenario=winter_storm")["body"]
    assert storm["assumptions"]["scenario"] == "winter_storm"
    assert any(w["code"] == "SIMULATED_WEATHER" for w in storm["warnings"])
    a_calm = next(r for r in calm["routes"] if r["id"] == "A")["stats"]["avg_risk"]
    a_storm = next(r for r in storm["routes"] if r["id"] == "A")["stats"]["avg_risk"]
    assert a_storm > a_calm


def test_far_departure_flags_low_confidence(client: APIClient) -> None:
    plan = post(client, departure_time=(next_hour() + timedelta(days=6)).isoformat())["body"]
    assert all(cp["low_confidence"] for cp in plan["routes"][0]["checkpoints"])
    assert any(w["code"] == "LOW_CONFIDENCE_FORECAST" for w in plan["warnings"])


class OneRoute(FakeRouting):
    ALTERNATIVES = ((0.0, 31.3, "I 80"),)

    async def route(self, *args: object, via: object = None, **kw: object) -> list:  # type: ignore[override]
        if via is not None:
            return []
        return await super().route(*args, **kw)  # type: ignore[arg-type]


def test_fewer_than_three_routes_warns(client: APIClient) -> None:
    with use_providers(Providers(OneRoute(), FakeGeocoding(), FakeWeather(), "fake")):
        plan = post(client)["body"]
    assert len(plan["routes"]) == 1
    assert plan["warnings"][0] == {
        "code": "ONLY_N_DISTINCT_ROUTES",
        "detail": "Only 1 distinct route exists for this trip.",
    }


class GappyWeather(FakeWeather):
    async def hourly(self, points, start, end):  # type: ignore[no-untyped-def]
        series = await super().hourly(points, start, end)
        return [
            s
            if i % 3
            else type(s)(s.times, s.wind_mph, (None,) * len(s.times), s.rain_in_hr, s.snow_in_hr)
            for i, s in enumerate(series)
        ]


def test_weather_gaps_are_unknown_and_excluded(client: APIClient) -> None:
    with use_providers(Providers(FakeRouting(), FakeGeocoding(), GappyWeather(), "fake")):
        plan = post(client)["body"]
    route = plan["routes"][0]
    unknown = [cp for cp in route["checkpoints"] if cp["levels"]["overall"] == "UNKNOWN"]
    assert unknown and all(cp["weather"]["gust_mph"] is None for cp in unknown)
    assert route["stats"]["unknown_mi"] > 0
    assert any(w["code"] == "WEATHER_GAPS" for w in plan["warnings"])


# --- validation (D-17) ---


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"load_weight_lb": 0}, "load_weight_lb"),
        ({"load_weight_lb": 80_001}, "load_weight_lb"),
        ({"load_weight_lb": 42000.5}, "load_weight_lb"),
        ({"sample_interval_mi": 30}, "sample_interval_mi"),
        ({"departure_time": "2020-01-01T00:00:00Z"}, "departure_time"),
        ({"departure_time": (next_hour() + timedelta(days=8)).isoformat()}, "departure_time"),
        ({"destination": {"lat": 39.7392, "lon": -104.9903}}, "non_field_errors"),
        ({"origin": {"lat": 91, "lon": 0}}, "origin"),
    ],
)
def test_validation_errors(client: APIClient, overrides: dict, field: str) -> None:
    r = post(client, **overrides)
    assert r["status"] == 400
    body = r["body"]
    assert body["code"] == "VALIDATION_ERROR" and field in body["errors"]
    assert r["headers"]["Content-Type"] == "application/problem+json"


def test_load_bounds_are_inclusive(client: APIClient) -> None:
    assert post(client, load_weight_lb=1)["status"] == 200
    assert post(client, load_weight_lb=80_000)["status"] == 200


def test_departure_within_the_past_hour_is_allowed(client: APIClient) -> None:
    recent = datetime.now(UTC) - timedelta(minutes=50)
    assert post(client, departure_time=recent.isoformat())["status"] == 200


def test_unknown_scenario_rejected(client: APIClient) -> None:
    assert post(client, "?scenario=hurricane")["status"] == 400


def test_malformed_json(client: APIClient) -> None:
    r = client.post("/api/v1/plans", "{nope", content_type="application/json")
    assert r.status_code == 400 and r.json()["code"] == "VALIDATION_ERROR"


# --- errors ---


def test_no_route_is_422(client: APIClient) -> None:
    r = post(client, destination={"lat": 51.5072, "lon": -0.1276})
    assert r["status"] == 422
    assert ProblemSerializer(data=r["body"]).is_valid()
    assert r["body"]["code"] == "NO_ROUTE"


def test_route_too_long_is_422(client: APIClient) -> None:
    r = post(client, origin={"lat": 25.77, "lon": -80.19}, destination={"lat": 61.2, "lon": -149.9})
    assert r["status"] == 422 and r["body"]["code"] == "ROUTE_TOO_LONG"


class DownWeather(FakeWeather):
    async def hourly(self, points, start, end):  # type: ignore[no-untyped-def]
        raise ProviderUnavailableError("The weather service returned an error.")


def test_provider_down_is_503(client: APIClient) -> None:
    with use_providers(Providers(FakeRouting(), FakeGeocoding(), DownWeather(), "fake")):
        r = post(client)
    assert r["status"] == 503 and r["body"]["code"] == "PROVIDER_UNAVAILABLE"
    assert r["body"]["detail"] == "The weather service returned an error."
