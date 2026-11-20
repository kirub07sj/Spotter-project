"""Provider Protocols. Services depend on these, never on concrete classes."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any, Protocol

from planner.domain.models import HourlySeries, LatLon, Place, RouteGeometry


class RoutingProvider(Protocol):
    async def route(
        self,
        origin: LatLon,
        destination: LatLon,
        *,
        via: LatLon | None = None,
        alternatives: bool = True,
        load_lb: float = 0.0,
    ) -> list[RouteGeometry]:
        """Routes in provider order. Raises NoRouteError or ProviderUnavailableError."""
        ...


class GeocodingProvider(Protocol):
    async def search(self, query: str, limit: int) -> list[Place]: ...


class WeatherProvider(Protocol):
    async def hourly(
        self, points: Sequence[LatLon], start: datetime, end: datetime
    ) -> list[HourlySeries]:
        """One series per point, in the same order, covering [start, end] hourly, in
        domain units. Missing values are None."""
        ...


class Cache(Protocol):
    async def get(self, key: str) -> Any | None: ...

    async def set(self, key: str, value: Any, ttl_s: int) -> None: ...


class DictCache:
    """In-memory cache for tests and the fakes. TTLs are ignored."""

    def __init__(self) -> None:
        self.data: dict[str, Any] = {}

    async def get(self, key: str) -> Any | None:
        return self.data.get(key)

    async def set(self, key: str, value: Any, ttl_s: int) -> None:
        self.data[key] = value
