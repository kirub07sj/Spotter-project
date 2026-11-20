from collections.abc import Callable
from typing import Any

import httpx
import pytest
import respx

from planner.domain.errors import ProviderUnavailableError
from planner.providers.base import DictCache
from planner.providers.http import HttpClient
from planner.providers.mapbox_geocoding import BASE_URL, MapboxGeocoding, normalize_query


def test_normalize_query() -> None:
    assert normalize_query("  Salt   Lake  CITY ") == "salt lake city"


@respx.mock
async def test_parses_features_and_caches_by_normalized_query(
    http: HttpClient, load_fixture: Callable[[str], Any]
) -> None:
    route = respx.get(BASE_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("mapbox/geocode_denver.json"))
    )
    geo = MapboxGeocoding(http, DictCache(), "pk.t")
    places = await geo.search("Denver", 5)
    assert places[0].label == "Denver, Colorado, United States"
    assert places[0].position.lat == pytest.approx(39.7392)
    assert places[0].position.lon == pytest.approx(-104.9903)
    assert places[1].label == "Denton, Texas, United States"  # name + place_formatted
    params = route.calls.last.request.url.params
    assert params["country"] == "us,ca" and params["autocomplete"] == "true"
    await geo.search("  denver ", 5)
    assert route.call_count == 1


@respx.mock
async def test_error_is_unavailable(http: HttpClient) -> None:
    respx.get(BASE_URL).mock(return_value=httpx.Response(403, json={}))
    with pytest.raises(ProviderUnavailableError):
        await MapboxGeocoding(http, None, "pk.t").search("x", 5)


async def test_missing_token(http: HttpClient) -> None:
    with pytest.raises(ProviderUnavailableError, match="not configured"):
        await MapboxGeocoding(http, None, "").search("denver", 5)
