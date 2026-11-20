import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from planner.providers.registry import Providers, use_providers
from planner.tests.golden_providers import NoGeocoding

pytestmark = pytest.mark.usefixtures("fake_providers")


def test_geocode_results(client: APIClient) -> None:
    r = client.get("/api/v1/geocode", {"q": "denver", "limit": 3})
    assert r.status_code == 200
    (place,) = r.json()["results"]
    assert place["label"].startswith("Denver") and place["lat"] == pytest.approx(39.7392)


def test_geocode_not_found(client: APIClient, fake_providers: Providers) -> None:
    with use_providers(
        Providers(fake_providers.routing, NoGeocoding(), fake_providers.weather, "fake")
    ):
        r = client.get("/api/v1/geocode", {"q": "atlantis"})
    assert r.status_code == 404 and r.json()["code"] == "GEOCODE_NOT_FOUND"


def test_geocode_validation(client: APIClient) -> None:
    assert client.get("/api/v1/geocode", {"q": "x"}).status_code == 400
    assert client.get("/api/v1/geocode", {"q": "denver", "limit": 50}).status_code == 400


def test_throttle_returns_problem_json(client: APIClient) -> None:
    rates = {"plans": "30/min", "heatmaps": "30/min", "geocode": "2/min"}
    from django.conf import settings

    with override_settings(
        REST_FRAMEWORK={**settings.REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": rates}
    ):
        from rest_framework.throttling import ScopedRateThrottle

        ScopedRateThrottle.THROTTLE_RATES = rates
        try:
            codes = [client.get("/api/v1/geocode", {"q": "denver"}).status_code for _ in range(3)]
            last = client.get("/api/v1/geocode", {"q": "denver"})
        finally:
            ScopedRateThrottle.THROTTLE_RATES = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    assert codes[:2] == [200, 200] and codes[2] == 429
    assert last.json()["code"] == "RATE_LIMITED" and "Retry-After" in last
