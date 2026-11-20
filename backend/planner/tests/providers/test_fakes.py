from datetime import UTC, datetime, timedelta

import pytest

from planner.domain.errors import NoRouteError
from planner.domain.models import LatLon
from planner.providers.fakes import FakeGeocoding, FakeRouting, FakeWeather

DEN = LatLon(39.7392, -104.9903)
SLC = LatLon(40.7608, -111.891)


async def test_fake_routing_returns_two_routes_and_via_route() -> None:
    routing = FakeRouting()
    routes = await routing.route(DEN, SLC)
    assert len(routes) == 2
    assert routes[0].duration_s < routes[1].duration_s
    for r in routes:
        assert len(r.seg_dist_m) == len(r.seg_dur_s) == len(r.coords) - 1
        assert r.coords[0] == DEN and r.coords[-1] == SLC
    (via,) = await routing.route(DEN, SLC, via=LatLon(39.0, -108.0), alternatives=False)
    assert via.coords[0] == DEN
    assert len(await routing.route(DEN, SLC, alternatives=False)) == 1


async def test_fake_routing_has_no_route_across_the_ocean() -> None:
    with pytest.raises(NoRouteError):
        await FakeRouting().route(DEN, LatLon(51.5, -0.12))
    with pytest.raises(NoRouteError):
        await FakeRouting().route(DEN, SLC, via=LatLon(30.0, -10.0))


async def test_fake_weather_is_deterministic_and_hourly() -> None:
    start = datetime(2026, 11, 20, 13, 20, tzinfo=UTC)
    end = start + timedelta(hours=5)
    a = await FakeWeather().hourly([DEN, SLC], start, end)
    b = await FakeWeather().hourly([DEN, SLC], start, end)
    assert a == b
    assert len(a[0].times) == 6
    assert a[0].times[1] - a[0].times[0] == 3600


async def test_fake_geocoding() -> None:
    places = await FakeGeocoding().search("  SALT lake", 5)
    assert [p.label for p in places] == ["Salt Lake City, Utah, United States"]
    assert await FakeGeocoding().search("atlantis", 5) == []
