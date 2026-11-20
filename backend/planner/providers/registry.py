"""Wires providers from settings (`PROVIDERS=real|fake`). Tests override with
`use_providers(...)`."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.cache import cache as django_cache

from .base import GeocodingProvider, RoutingProvider, WeatherProvider
from .fakes import FakeGeocoding, FakeRouting, FakeWeather
from .http import HttpClient
from .mapbox_geocoding import MapboxGeocoding
from .mapbox_routing import MapboxRouting
from .open_meteo import OpenMeteoWeather


@dataclass(frozen=True)
class Providers:
    routing: RoutingProvider
    geocoding: GeocodingProvider
    weather: WeatherProvider
    name: str


class DjangoCache:
    async def get(self, key: str) -> Any | None:
        return await django_cache.aget(key)

    async def set(self, key: str, value: Any, ttl_s: int) -> None:
        await django_cache.aset(key, value, ttl_s)


_override: Providers | None = None


def build_providers() -> Providers:
    if settings.PROVIDERS == "fake":
        return Providers(FakeRouting(), FakeGeocoding(), FakeWeather(), "fake")
    http, cache = HttpClient(), DjangoCache()
    return Providers(
        routing=MapboxRouting(
            http,
            cache,
            settings.MAPBOX_TOKEN,
            use_max_weight=settings.MAPBOX_USE_MAX_WEIGHT,
            tare_lb=settings.TRACTOR_TRAILER_TARE_LB,
        ),
        geocoding=MapboxGeocoding(http, cache, settings.MAPBOX_TOKEN),
        weather=OpenMeteoWeather(
            http, cache, settings.OPEN_METEO_BASE_URL, settings.OPEN_METEO_API_KEY
        ),
        name="real",
    )


def get_providers() -> Providers:
    return _override or build_providers()


@contextmanager
def use_providers(providers: Providers) -> Iterator[Providers]:
    global _override
    previous, _override = _override, providers
    try:
        yield providers
    finally:
        _override = previous
