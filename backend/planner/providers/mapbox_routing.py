"""Mapbox Directions adapter (docs/03 §2)."""

import logging
from typing import Any

import polyline

from planner.domain.errors import NoRouteError, ProviderUnavailableError
from planner.domain.geo import segment_lengths_m
from planner.domain.models import LatLon, RouteGeometry
from planner.domain.units import lb_to_t

from .base import Cache
from .http import HttpClient

log = logging.getLogger(__name__)

BASE_URL = "https://api.mapbox.com/directions/v5/mapbox/driving"
CACHE_TTL_S = 30 * 60
MAX_WEIGHT_T = 100.0
NO_ROUTE_CODES = frozenset({"NoRoute", "NoSegment"})


def _lonlat(p: LatLon) -> str:
    return f"{p.lon:.6f},{p.lat:.6f}"  # Mapbox takes longitude first


def _key(p: LatLon) -> str:
    return f"{p.lat:.4f},{p.lon:.4f}"


class MapboxRouting:
    def __init__(
        self,
        http: HttpClient,
        cache: Cache | None,
        token: str,
        *,
        use_max_weight: bool = False,
        tare_lb: float = 35_000.0,
        base_url: str = BASE_URL,
    ) -> None:
        self.http, self.cache, self.token = http, cache, token
        self.use_max_weight, self.tare_lb, self.base_url = use_max_weight, tare_lb, base_url

    def gross_tonnes(self, load_lb: float) -> float:
        return round(min(MAX_WEIGHT_T, lb_to_t(load_lb + self.tare_lb)), 1)

    async def route(
        self,
        origin: LatLon,
        destination: LatLon,
        *,
        via: LatLon | None = None,
        alternatives: bool = True,
        load_lb: float = 0.0,
    ) -> list[RouteGeometry]:
        if not self.token:
            raise ProviderUnavailableError("Routing is not configured (MAPBOX_TOKEN is empty).")
        stops = [origin, *([via] if via else []), destination]
        params: dict[str, str | int | float] = {
            "alternatives": "true" if alternatives else "false",
            "geometries": "polyline6",
            "overview": "full",
            "annotations": "distance,duration",
            "steps": "false",
            "access_token": self.token,
        }
        max_weight = self.gross_tonnes(load_lb) if self.use_max_weight else None
        if max_weight is not None:
            params["max_weight"] = max_weight
        key = f"rt:{':'.join(_key(s) for s in stops)}:{alternatives}:{max_weight}"
        body = await self.cache.get(key) if self.cache else None
        if body is None:
            url = f"{self.base_url}/{';'.join(_lonlat(s) for s in stops)}"
            status, body = await self.http.get_json(url, params, provider="mapbox_directions")
            _raise_for_body(status, body)
            if self.cache:
                await self.cache.set(key, body, CACHE_TTL_S)
        return [parse_route(r) for r in body["routes"]]


def _raise_for_body(status: int, body: Any) -> None:
    code = body.get("code") if isinstance(body, dict) else None
    if code in NO_ROUTE_CODES:
        raise NoRouteError("No drivable route was found between these points.")
    if status != 200 or code != "Ok":
        log.warning("mapbox directions error", extra={"status": status, "code": code})
        raise ProviderUnavailableError("The routing service returned an error.")
    if not body.get("routes"):
        raise NoRouteError("No drivable route was found between these points.")


def parse_route(raw: dict[str, Any]) -> RouteGeometry:
    coords = tuple(LatLon(lat, lon) for lat, lon in polyline.decode(raw["geometry"], 6))
    legs = raw.get("legs") or []
    dist: list[float] = []
    dur: list[float] = []
    for leg in legs:
        annotation = leg.get("annotation") or {}
        dist.extend(annotation.get("distance") or [])
        dur.extend(annotation.get("duration") or [])
    summary = ", ".join(dict.fromkeys(s for leg in legs if (s := leg.get("summary", ""))))
    n = len(coords) - 1
    if len(dist) != n or len(dur) != n:
        # docs/03 §2 fallback: haversine distances, total duration spread by distance.
        log.warning("mapbox annotations missing or mismatched", extra={"coords": len(coords)})
        dist = list(segment_lengths_m(coords))
        total = sum(dist) or 1.0
        dur = [float(raw["duration"]) * d / total for d in dist]
    return RouteGeometry(
        coords=coords, seg_dist_m=tuple(dist), seg_dur_s=tuple(dur), summary=summary
    )
