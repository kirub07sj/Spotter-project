from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
import respx

from planner.domain.errors import ProviderUnavailableError
from planner.domain.models import LatLon
from planner.domain.units import cm_to_in, kmh_to_mph, mm_to_in
from planner.providers.base import DictCache
from planner.providers.http import HttpClient
from planner.providers.open_meteo import OpenMeteoWeather

BASE = "https://api.open-meteo.test/v1/forecast"
START = datetime(2026, 11, 20, 13, tzinfo=UTC)
END = datetime(2026, 11, 21, 12, tzinfo=UTC)
PTS = [LatLon(39.7392, -104.9903), LatLon(41.3114, -105.5911), LatLon(39.0639, -108.5506)]


def weather(http: HttpClient, cache: DictCache | None = None, key: str = "") -> OpenMeteoWeather:
    return OpenMeteoWeather(http, cache, BASE, key)


@respx.mock
async def test_multi_point_parse_and_unit_conversion(
    http: HttpClient, load_fixture: Callable[[str], Any]
) -> None:
    raw = load_fixture("open_meteo/multi_point_winter.json")
    route = respx.get(BASE).mock(return_value=httpx.Response(200, json=raw))
    series = await weather(http).hourly(PTS, START, END)
    assert len(series) == 3
    h = raw[1]["hourly"]
    s = series[1]
    assert s.times == tuple(h["time"])
    assert s.gust_mph[10] == pytest.approx(kmh_to_mph(h["wind_gusts_10m"][10]))
    assert s.wind_mph[10] == pytest.approx(kmh_to_mph(h["wind_speed_10m"][10]))
    assert s.snow_in_hr[10] == pytest.approx(cm_to_in(h["snowfall"][10]))
    h0 = raw[2]["hourly"]  # D-05: rain rate is rain + showers
    assert series[2].rain_in_hr[10] == pytest.approx(mm_to_in(h0["rain"][10] + h0["showers"][10]))
    params = route.calls.last.request.url.params
    assert params["latitude"] == "39.74,41.31,39.06"
    assert params["longitude"] == "-104.99,-105.59,-108.55"
    assert params["hourly"] == "wind_speed_10m,wind_gusts_10m,rain,showers,snowfall"
    assert params["timezone"] == "GMT" and params["timeformat"] == "unixtime"
    assert params["start_hour"] == "2026-11-20T13:00" and params["end_hour"] == "2026-11-21T12:00"
    assert "apikey" not in params


@respx.mock
async def test_nonzero_snow_and_rain_units_with_synthetic_stress_fixture(
    http: HttpClient, load_fixture: Callable[[str], Any]
) -> None:
    # Calm real recordings must not erase the nonzero conversion checks.
    raw = load_fixture("open_meteo/unit_conversion.json")
    respx.get(BASE).mock(return_value=httpx.Response(200, json=raw))
    series = await weather(http).hourly(PTS, START, END)
    assert series[1].snow_in_hr[10] == pytest.approx(cm_to_in(4.2))
    assert series[2].rain_in_hr[10] == pytest.approx(mm_to_in(0.4 + 0.3))


@respx.mock
async def test_single_point_object_response(
    http: HttpClient, load_fixture: Callable[[str], Any]
) -> None:
    respx.get(BASE).mock(
        return_value=httpx.Response(200, json=load_fixture("open_meteo/single_point.json"))
    )
    (s,) = await weather(http, key="k").hourly([LatLon(40.76, -111.89)], START, END)
    assert len(s.times) == 6
    assert respx.calls.last.request.url.params["apikey"] == "k"


@respx.mock
async def test_nulls_stay_missing(http: HttpClient, load_fixture: Callable[[str], Any]) -> None:
    respx.get(BASE).mock(
        return_value=httpx.Response(200, json=load_fixture("open_meteo/nulls.json"))
    )
    s, calm = await weather(http).hourly(
        [LatLon(41.79, -107.24), LatLon(41.59, -109.2)], START, END
    )
    assert s.gust_mph[3] is None and s.snow_in_hr[3] is None
    assert s.rain_in_hr[5] is None  # rain null: the sum is missing, not just showers
    assert s.wind_mph[3] is not None
    assert None not in calm.gust_mph


@respx.mock
async def test_dedupes_and_returns_in_request_order(
    http: HttpClient, load_fixture: Callable[[str], Any]
) -> None:
    raw = load_fixture("open_meteo/multi_point_winter.json")
    respx.get(BASE).mock(return_value=httpx.Response(200, json=raw[:2]))
    a, b = PTS[0], PTS[1]
    near_a = LatLon(a.lat + 0.001, a.lon - 0.001)  # same 2 dp key
    series = await weather(http).hourly([a, b, near_a], START, END)
    assert respx.calls.last.request.url.params["latitude"] == "39.74,41.31"
    assert series[0] is series[2]


@respx.mock
async def test_chunks_of_100_fetched_in_parallel(
    http: HttpClient, load_fixture: Callable[[str], Any]
) -> None:
    template = load_fixture("open_meteo/single_point.json")

    def respond(request: httpx.Request) -> httpx.Response:
        n = len(request.url.params["latitude"].split(","))
        return httpx.Response(200, json=[template] * n)

    route = respx.get(BASE).mock(side_effect=respond)
    pts = [LatLon(30 + i * 0.05, -100.0) for i in range(250)]
    series = await weather(http).hourly(pts, START, END)
    sizes = sorted(len(c.request.url.params["latitude"].split(",")) for c in route.calls)
    assert sizes == [50, 100, 100]
    assert len(series) == 250


@respx.mock
async def test_cache_hit_skips_network(
    http: HttpClient, load_fixture: Callable[[str], Any]
) -> None:
    raw = load_fixture("open_meteo/multi_point_winter.json")
    route = respx.get(BASE).mock(return_value=httpx.Response(200, json=raw))
    w = weather(http, DictCache())
    first = await w.hourly(PTS, START, END)
    second = await w.hourly(PTS, START, END)
    assert route.call_count == 1 and first == second


@respx.mock
async def test_wrong_location_count_is_unavailable(
    http: HttpClient, load_fixture: Callable[[str], Any]
) -> None:
    raw = load_fixture("open_meteo/multi_point_winter.json")
    respx.get(BASE).mock(return_value=httpx.Response(200, json=raw[:1]))
    with pytest.raises(ProviderUnavailableError, match="unexpected shape"):
        await weather(http).hourly(PTS, START, END)


@respx.mock
async def test_ragged_columns_are_unavailable(
    http: HttpClient, load_fixture: Callable[[str], Any]
) -> None:
    raw = load_fixture("open_meteo/single_point.json")
    raw["hourly"]["snowfall"].pop()
    respx.get(BASE).mock(return_value=httpx.Response(200, json=raw))
    with pytest.raises(ProviderUnavailableError):
        await weather(http).hourly([PTS[0]], START, END)


@respx.mock
async def test_400_is_unavailable(http: HttpClient) -> None:
    respx.get(BASE).mock(return_value=httpx.Response(400, json={"error": True}))
    with pytest.raises(ProviderUnavailableError):
        await weather(http).hourly([PTS[0]], START, END)
