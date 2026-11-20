from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from planner.providers.fakes import FakeGeocoding, FakeRouting, FakeWeather
from planner.providers.registry import Providers, use_providers


@pytest.fixture(autouse=True)
def _clear_cache() -> Iterator[None]:
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def fake_providers() -> Iterator[Providers]:
    with use_providers(Providers(FakeRouting(), FakeGeocoding(), FakeWeather(), "fake")) as p:
        yield p


def next_hour() -> datetime:
    now = datetime.now(UTC)
    return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)


def plan_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "origin": {"lat": 39.7392, "lon": -104.9903, "label": "Denver, CO"},
        "destination": {"lat": 40.7608, "lon": -111.891, "label": "Salt Lake City, UT"},
        "departure_time": next_hour().isoformat(),
        "load_weight_lb": 42_000,
        "sample_interval_mi": 25,
    }
    body.update(overrides)
    return body
