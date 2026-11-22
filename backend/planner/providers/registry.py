"""Wires providers from settings (`PROVIDERS=real|fake`). Tests override with
`use_providers(...)`."""

import asyncio
import logging
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

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Providers:
    routing: RoutingProvider
    geocoding: GeocodingProvider
    weather: WeatherProvider
    name: str


class DjangoCache:
    _disabled = False

    async def get(self, key: str) -> Any | None:
        if self._disabled:
            return None
        try:
            return await asyncio.wait_for(django_cache.aget(key), timeout=0.5)
        except Exception:
            log.warning("cache.get failed, bypassing cache for this worker", exc_info=True)
            self._disabled = True
            return None

    async def set(self, key: str, value: Any, ttl_s: int) -> None:
        if self._disabled:
            return
        try:
            await asyncio.wait_for(django_cache.aset(key, value, ttl_s), timeout=0.5)
        except Exception:
            log.warning("cache.set failed, bypassing cache for this worker", exc_info=True)
            self._disabled = True


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
