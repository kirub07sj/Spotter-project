import logging
from collections.abc import Callable
from typing import Any

import httpx
import pytest
import respx

from planner.domain.errors import NoRouteError, ProviderUnavailableError
from planner.domain.models import LatLon
from planner.domain.units import m_to_mi
from planner.providers.base import DictCache
from planner.providers.http import HttpClient
from planner.providers.mapbox_routing import BASE_URL, MapboxRouting, parse_route

TOKEN = "pk.secret-test-token"
DEN = LatLon(39.7392, -104.9903)
SLC = LatLon(40.7608, -111.891)
LONLAT_PATH = "-104.990300,39.739200;-111.891000,40.760800"


def adapter(http: HttpClient, **kw: Any) -> MapboxRouting:
    return MapboxRouting(http, DictCache(), TOKEN, **kw)


@respx.mock
async def test_parses_three_routes_with_annotations(
    http: HttpClient, load_fixture: Callable[[str], Any]
) -> None:
    route = respx.get(f"{BASE_URL}/{LONLAT_PATH}").mock(
        return_value=httpx.Response(200, json=load_fixture("mapbox/denver_slc.json"))
    )
    routes = await adapter(http).route(DEN, SLC)
    assert len(routes) == 3
    for r in routes:
        assert len(r.seg_dist_m) == len(r.seg_dur_s) == len(r.coords) - 1
        assert r.coords[0].lat == pytest.approx(DEN.lat, abs=1e-5)  # decoded as lat, lon
        assert r.coords[-1].lon == pytest.approx(SLC.lon, abs=1e-5)
    assert routes[0].summary == "I 80, I 25"
    assert 400 < m_to_mi(routes[0].distance_m) < 700
    params = route.calls.last.request.url.params
    assert params["geometries"] == "polyline6" and params["overview"] == "full"
    assert params["annotations"] == "distance,duration" and params["alternatives"] == "true"
    assert "max_weight" not in params


@respx.mock
async def test_via_request_has_three_stops_and_concatenates_legs(
    http: HttpClient, load_fixture: Callable[[str], Any]
) -> None:
    via = LatLon(39.3, -108.2)
    route = respx.get(url__startswith=BASE_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("mapbox/via_two_legs.json"))
    )
    (r,) = await adapter(http).route(DEN, SLC, via=via, alternatives=False)
    assert route.calls.last.request.url.path.endswith(
        "-104.990300,39.739200;-108.200000,39.300000;-111.891000,40.760800"
    )
    assert route.calls.last.request.url.params["alternatives"] == "false"
    assert len(r.seg_dist_m) == len(r.coords) - 1
    assert r.summary == "I 70, US 6, I 15"


@respx.mock
async def test_max_weight_sent_only_when_enabled(
    http: HttpClient, load_fixture: Callable[[str], Any]
) -> None:
    route = respx.get(url__startswith=BASE_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("mapbox/short_trip.json"))
    )
    routing = adapter(http, use_max_weight=True, tare_lb=35_000)
    await routing.route(DEN, SLC, load_lb=42_000)
    assert route.calls.last.request.url.params["max_weight"] == "34.9"  # 77,000 lb in t
    assert routing.gross_tonnes(500_000) == 100.0


@respx.mock
async def test_no_route_maps_to_no_route_error(
    http: HttpClient, load_fixture: Callable[[str], Any]
) -> None:
    respx.get(url__startswith=BASE_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("mapbox/no_route.json"))
    )
    with pytest.raises(NoRouteError):
        await adapter(http).route(DEN, LatLon(51.5, -0.12))


@respx.mock
async def test_no_segment_422_is_no_route(http: HttpClient) -> None:
    respx.get(url__startswith=BASE_URL).mock(
        return_value=httpx.Response(422, json={"code": "NoSegment", "message": "x"})
    )
    with pytest.raises(NoRouteError):
        await adapter(http).route(DEN, SLC)


@respx.mock
async def test_ok_with_empty_routes_is_no_route(http: HttpClient) -> None:
    respx.get(url__startswith=BASE_URL).mock(
        return_value=httpx.Response(200, json={"code": "Ok", "routes": []})
    )
    with pytest.raises(NoRouteError):
        await adapter(http).route(DEN, SLC)


@respx.mock
async def test_other_errors_are_unavailable_and_never_leak_token(
    http: HttpClient, caplog: pytest.LogCaptureFixture
) -> None:
    respx.get(url__startswith=BASE_URL).mock(
        return_value=httpx.Response(401, json={"message": f"Not Authorized - {TOKEN}"})
    )
    caplog.set_level(logging.DEBUG)
    with pytest.raises(ProviderUnavailableError) as err:
        await adapter(http).route(DEN, SLC)
    assert TOKEN not in str(err.value)
    assert TOKEN not in caplog.text


@respx.mock
async def test_5xx_retries_exhausted(http: HttpClient) -> None:
    route = respx.get(url__startswith=BASE_URL).mock(return_value=httpx.Response(502))
    with pytest.raises(ProviderUnavailableError):
        await adapter(http).route(DEN, SLC)
    assert route.call_count == 3


@respx.mock
async def test_cache_hit_skips_network(
    http: HttpClient, load_fixture: Callable[[str], Any]
) -> None:
    route = respx.get(url__startswith=BASE_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("mapbox/short_trip.json"))
    )
    routing = adapter(http)
    first = await routing.route(DEN, SLC)
    second = await routing.route(LatLon(39.73921, -104.99031), SLC)  # same 4 dp key
    assert route.call_count == 1 and first == second


async def test_missing_token_is_unavailable(http: HttpClient) -> None:
    with pytest.raises(ProviderUnavailableError, match="not configured"):
        await MapboxRouting(http, None, "").route(DEN, SLC)


def test_annotation_mismatch_falls_back_to_haversine(
    load_fixture: Callable[[str], Any], caplog: pytest.LogCaptureFixture
) -> None:
    raw = load_fixture("mapbox/short_trip.json")["routes"][0]
    raw["legs"][0]["annotation"]["distance"].pop()
    r = parse_route(raw)
    assert len(r.seg_dist_m) == len(r.coords) - 1
    assert r.duration_s == pytest.approx(raw["duration"])
    assert "mismatched" in caplog.text
