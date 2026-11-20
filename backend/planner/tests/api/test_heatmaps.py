import base64
from datetime import datetime

import numpy as np
import pytest
from rest_framework.test import APIClient

from planner.api.serializers import HeatmapResponseSerializer
from planner.domain.levels import Level
from planner.domain.risk import classify_checkpoint
from planner.services.encoding import encode
from planner.tests.api.conftest import next_hour, plan_body

pytestmark = pytest.mark.usefixtures("fake_providers")


def make_plan(client: APIClient, query: str = "", **kw: object) -> dict:
    return client.post(f"/api/v1/plans{query}", plan_body(**kw), format="json").json()


def heatmap_body(plan: dict, scenario: str | None = None) -> dict:
    return {
        "routes": [r["geometry"] for r in plan["routes"]],
        "departure_time": plan["assumptions"]["departure_time"],
        "load_weight_lb": plan["assumptions"]["load_weight_lb"],
        "scenario": scenario,
    }


def decode(body: dict) -> tuple[np.ndarray, np.ndarray]:
    g = body["grid"]
    rows, cols = g["rows"], g["cols"]
    bits = np.frombuffer(base64.b64decode(body["mask"]), dtype=np.uint8)
    mask = np.unpackbits(bits, bitorder="little")[: rows * cols].reshape(rows, cols).astype(bool)
    scores = np.frombuffer(base64.b64decode(body["scores"]), dtype=np.uint8)
    return mask, scores.reshape(49, rows, cols)


def test_heatmap_contract_and_49_hours(client: APIClient) -> None:
    plan = make_plan(client)
    r = client.post("/api/v1/heatmaps", heatmap_body(plan), format="json")
    assert r.status_code == 200, r.content
    body = r.json()
    assert HeatmapResponseSerializer(data=body).is_valid(raise_exception=True)
    assert len(body["hours"]) == 49
    hours = [datetime.fromisoformat(h) for h in body["hours"]]
    assert hours[0] == datetime.fromisoformat(plan["assumptions"]["departure_time"])
    assert (hours[-1] - hours[0]).total_seconds() == 48 * 3600
    mask, scores = decode(body)
    assert 0 < mask.sum() <= 450
    assert (scores[:, ~mask] == 255).all()
    assert (scores[:, mask] <= 200).all()
    assert "weather;dur=" in r["Server-Timing"]


async def test_heatmap_cells_match_checkpoint_classification() -> None:
    """D-15: for the same weather, floor(decoded cell score) is exactly the level
    classify_checkpoint gives, at every masked cell and hour, under a storm scenario so
    every level occurs."""
    from planner.domain.geo import cumulative, segment_lengths_m
    from planner.domain.heatmap import SCORE_SCALE
    from planner.domain.models import LatLon
    from planner.domain.scenarios import apply_delta, scenario_delta
    from planner.domain.weather_lookup import sample_for
    from planner.providers.fakes import FakeGeocoding, FakeRouting, FakeWeather
    from planner.providers.registry import Providers
    from planner.services.heatmap_service import (
        HeatmapConfig,
        HeatmapRequest,
        create_heatmap,
    )
    from planner.services.plan_service import scenario_anchor
    from planner.services.timing import Timings

    route = [LatLon(39.74 + 0.01 * i, -104.99 - 0.069 * i) for i in range(101)]
    depart = next_hour()
    load = 42_000
    req = HeatmapRequest([route], depart, load, "winter_storm")
    weather = FakeWeather()
    providers = Providers(FakeRouting(), FakeGeocoding(), weather, "fake")
    hm = await create_heatmap(req, providers, HeatmapConfig("gust", 40, 150), Timings())
    g = hm.grid
    mask = np.unpackbits(np.frombuffer(hm.mask, np.uint8), bitorder="little")
    mask = mask[: g.rows * g.cols].reshape(g.rows, g.cols).astype(bool)
    scores = np.frombuffer(hm.scores, np.uint8).reshape(49, g.rows, g.cols)
    lat, lon = g.cell_centers()
    anchor = scenario_anchor("winter_storm", route, cumulative(segment_lengths_m(route)), depart)
    seen = set()
    for r, c in zip(*np.nonzero(mask), strict=True):
        p = LatLon(float(lat[r, c]), float(lon[r, c]))
        (series,) = await weather.hourly([p], hm.hours[0], hm.hours[-1])
        for k in range(0, 49, 4):
            ws = sample_for(series, hm.hours[k])
            ws = apply_delta(ws, scenario_delta("winter_storm", anchor, p, ws.forecast_hour))
            level = classify_checkpoint(ws, load, "gust").overall
            assert int(scores[k, r, c]) // SCORE_SCALE == int(level), (r, c, k)
            seen.add(level)
    assert {Level.LOW, Level.NO_TRAVEL} <= seen


@pytest.mark.parametrize(
    ("override", "status"),
    [
        ({"routes": []}, 400),
        ({"routes": ["x"] * 4}, 400),
        ({"routes": ["not a polyline ~~~"]}, 400),
        ({"load_weight_lb": 0}, 400),
        ({"scenario": "tornado"}, 400),
    ],
)
def test_heatmap_validation(client: APIClient, override: dict, status: int) -> None:
    body = {
        "routes": [encode([])],
        "departure_time": next_hour().isoformat(),
        "load_weight_lb": 1000,
        **override,
    }
    assert client.post("/api/v1/heatmaps", body, format="json").status_code == status


def test_heatmap_rejects_oversized_routes(client: APIClient) -> None:
    from planner.domain.models import LatLon

    huge = encode([LatLon(40 + i * 1e-4, -105.0) for i in range(5_001)])
    body = {"routes": [huge], "departure_time": next_hour().isoformat(), "load_weight_lb": 1000}
    r = client.post("/api/v1/heatmaps", body, format="json")
    assert r.status_code == 400 and "5,000" in r.json()["detail"]


def test_heatmap_departure_window(client: APIClient) -> None:
    body = {"routes": [encode([])], "departure_time": "2020-01-01T00:00:00Z", "load_weight_lb": 1}
    r = client.post("/api/v1/heatmaps", body, format="json")
    assert r.status_code == 400 and "departure_time" in r.json()["errors"]
