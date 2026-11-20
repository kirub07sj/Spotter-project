"""Open-Meteo hourly forecast adapter (docs/03 §6). Requests metric defaults and converts
once, here, through domain/units.py."""

import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from planner.domain.errors import ProviderUnavailableError
from planner.domain.models import HourlySeries, LatLon
from planner.domain.units import cm_to_in, kmh_to_mph, mm_to_in

from .base import Cache
from .http import HttpClient

HOURLY_VARS = "wind_speed_10m,wind_gusts_10m,rain,showers,snowfall"
CHUNK_SIZE = 100
MAX_CONCURRENT = 4
CACHE_TTL_S = 30 * 60


def round_point(p: LatLon) -> LatLon:
    """~1 km dedupe and cache key resolution."""
    return LatLon(round(p.lat, 2), round(p.lon, 2))


def _hour_str(t: datetime) -> str:
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M")


def _conv(values: list[float | None], fn: Any) -> tuple[float | None, ...]:
    return tuple(None if v is None else fn(v) for v in values)


def parse_location(raw: dict[str, Any]) -> HourlySeries:
    h = raw["hourly"]
    times = [int(t) for t in h["time"]]
    n = len(times)
    columns = [
        h.get(k) for k in ("wind_speed_10m", "wind_gusts_10m", "rain", "showers", "snowfall")
    ]
    if any(c is None or len(c) != n for c in columns):
        raise ProviderUnavailableError("The weather service returned an unexpected shape.")
    wind, gust, rain, showers, snow = columns
    # D-05: rain rate = rain + showers (liquid only); `precipitation` would double count snow.
    liquid = [None if r is None or s is None else r + s for r, s in zip(rain, showers, strict=True)]
    return HourlySeries(
        times=tuple(times),
        wind_mph=_conv(wind, kmh_to_mph),
        gust_mph=_conv(gust, kmh_to_mph),
        rain_in_hr=_conv(liquid, mm_to_in),
        snow_in_hr=_conv(snow, cm_to_in),
    )


class OpenMeteoWeather:
    def __init__(
        self, http: HttpClient, cache: Cache | None, base_url: str, api_key: str = ""
    ) -> None:
        self.http, self.cache, self.base_url, self.api_key = http, cache, base_url, api_key

    async def hourly(
        self, points: Sequence[LatLon], start: datetime, end: datetime
    ) -> list[HourlySeries]:
        start_s, end_s = _hour_str(start), _hour_str(end)
        keys = [round_point(p) for p in points]
        unique = list(dict.fromkeys(keys))
        found: dict[LatLon, HourlySeries] = {}
        if self.cache:
            for p in unique:
                hit = await self.cache.get(self._cache_key(p, start_s, end_s))
                if hit is not None:
                    found[p] = hit
        missing = [p for p in unique if p not in found]
        chunks = [missing[i : i + CHUNK_SIZE] for i in range(0, len(missing), CHUNK_SIZE)]
        sem = asyncio.Semaphore(MAX_CONCURRENT)

        async def fetch(chunk: list[LatLon]) -> list[HourlySeries]:
            async with sem:
                return await self._fetch_chunk(chunk, start_s, end_s)

        for chunk, series in zip(
            chunks, await asyncio.gather(*(fetch(c) for c in chunks)), strict=True
        ):
            for p, s in zip(chunk, series, strict=True):
                found[p] = s
                if self.cache:
                    await self.cache.set(self._cache_key(p, start_s, end_s), s, CACHE_TTL_S)
        return [found[k] for k in keys]

    @staticmethod
    def _cache_key(p: LatLon, start_s: str, end_s: str) -> str:
        return f"wx:{p.lat:.2f}:{p.lon:.2f}:{start_s}:{end_s}"

    async def _fetch_chunk(
        self, chunk: list[LatLon], start_s: str, end_s: str
    ) -> list[HourlySeries]:
        params: dict[str, str | int | float] = {
            "latitude": ",".join(f"{p.lat:.2f}" for p in chunk),
            "longitude": ",".join(f"{p.lon:.2f}" for p in chunk),
            "hourly": HOURLY_VARS,
            "timezone": "GMT",
            "timeformat": "unixtime",
            "start_hour": start_s,
            "end_hour": end_s,
        }
        if self.api_key:
            params["apikey"] = self.api_key
        status, body = await self.http.get_json(self.base_url, params, provider="open_meteo")
        if status != 200 or body is None:
            raise ProviderUnavailableError("The weather service returned an error.")
        # A single coordinate returns an object, several return a list in request order.
        locations = body if isinstance(body, list) else [body]
        if len(locations) != len(chunk):
            raise ProviderUnavailableError("The weather service returned an unexpected shape.")
        return [parse_location(loc) for loc in locations]
