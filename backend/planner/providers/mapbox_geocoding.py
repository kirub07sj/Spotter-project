"""Mapbox Geocoding v6 adapter, proxied through /api/v1/geocode."""

import logging
import re
from typing import Any

from planner.domain.errors import ProviderUnavailableError
from planner.domain.models import LatLon, Place

from .base import Cache
from .http import HttpClient

log = logging.getLogger(__name__)

BASE_URL = "https://api.mapbox.com/search/geocode/v6/forward"
CACHE_TTL_S = 24 * 60 * 60


def normalize_query(q: str) -> str:
    return re.sub(r"\s+", " ", q.strip().lower())


class MapboxGeocoding:
    def __init__(
        self, http: HttpClient, cache: Cache | None, token: str, base_url: str = BASE_URL
    ) -> None:
        self.http, self.cache, self.token, self.base_url = http, cache, token, base_url

    async def search(self, query: str, limit: int) -> list[Place]:
        if not self.token:
            raise ProviderUnavailableError("Geocoding is not configured (MAPBOX_TOKEN is empty).")
        norm = normalize_query(query)
        key = f"geo:{norm}:{limit}"
        body = await self.cache.get(key) if self.cache else None
        if body is None:
            params: dict[str, str | int | float] = {
                "q": norm,
                "limit": limit,
                "country": "us,ca",
                "autocomplete": "true",
                "access_token": self.token,
            }
            status, body = await self.http.get_json(
                self.base_url, params, provider="mapbox_geocoding"
            )
            if status != 200 or not isinstance(body, dict):
                log.warning("mapbox geocoding error", extra={"status": status})
                raise ProviderUnavailableError("The geocoding service returned an error.")
            if self.cache:
                await self.cache.set(key, body, CACHE_TTL_S)
        return [_place(f) for f in body.get("features", [])]


def _place(feature: dict[str, Any]) -> Place:
    props = feature.get("properties", {})
    lon, lat = feature["geometry"]["coordinates"]
    label = props.get("full_address") or ", ".join(
        p for p in (props.get("name"), props.get("place_formatted")) if p
    )
    return Place(
        id=str(props.get("mapbox_id", feature.get("id", ""))),
        label=label,
        position=LatLon(float(lat), float(lon)),
    )
