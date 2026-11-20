---
name: provider-integration
description: Use when adding or changing calls to Mapbox Directions, Mapbox Geocoding or Open-Meteo, including batching, caching, retries, unit conversion, via-point alternative routes, recorded fixtures and fake providers in backend/planner/providers.
---

# Provider Integration

## Before you start
Read `docs/02-ARCHITECTURE.md` sections 5 and 6 and `docs/03-ALGORITHMS.md` sections 1 to 3 and 6.

## Shape of every adapter
```python
class OpenMeteoWeather(WeatherProvider):           # implements the Protocol from base.py
    def __init__(self, http: HttpClient, cache: Cache, base_url: str, api_key: str | None): ...
    async def hourly(self, points: Sequence[LatLon], start: datetime, end: datetime) -> list[HourlySeries]: ...
```
- Inject the HTTP client and cache, so tests swap in respx and a dict cache.
- Return **domain models in domain units**. Convert with `domain/units.py` inside the adapter, and nowhere else.
- Raise `ProviderUnavailableError` after retries, or `NoRouteError` for a valid "no route" answer. Never return partial garbage.

## Mapbox Directions
- Coordinates are **lon,lat**. This is the most common bug.
- `alternatives=true` gives at most 2 alternatives, and sometimes none. The via-point fallback in `domain/alternatives.py` fills the gap (D-13).
- Request `geometries=polyline6&overview=full&annotations=distance,duration&steps=false`.
- Check that the annotation arrays have length `len(coords) - 1`. If they don't, use the fallback in 03-ALGORITHMS section 2 and log it.
- `max_weight` is metric tons, 0 to 100. Only send it when `MAPBOX_USE_MAX_WEIGHT=true`.
- `code != "Ok"`: `NoRoute` maps to `NoRouteError`, and anything else to `ProviderUnavailableError`.

## Mapbox Geocoding
- Proxy through `/api/v1/geocode`. Default `country=us,ca`, `limit=5`, autocomplete on.
- Normalize the query (trim, lowercase, collapse spaces) before using it as a cache key. TTL 24h.

## Open-Meteo
- Request the default metric units and convert yourself (km/h to mph, mm to in, cm to in).
- Variables: `wind_speed_10m, wind_gusts_10m, rain, showers, snowfall`. Use `timezone=GMT&timeformat=unixtime`.
- Many coordinates per call: comma-separated `latitude` and `longitude`. The response is a list in request order. Chunk at 100 points, run the chunks in parallel (semaphore 4).
- Use `start_hour` / `end_hour` to fetch only the trip window. It keeps payloads small.
- Hourly rain, showers, snowfall and gusts describe the **preceding hour** (D-08).
- `null` values become missing, which leads to `UNKNOWN` downstream.
- The free tier is for non-commercial use. `OPEN_METEO_API_KEY` and base URL are configurable for a paid plan.

## Retries and timeouts (`providers/http.py`)
- Timeout 8 s total. Retry twice on timeouts, 429 and 5xx with backoff of 0.3 s and 0.9 s plus jitter. Honor `Retry-After`.
- Record each call's latency into the request's Server-Timing collector.

## Caching
Keys and TTLs are in `02-ARCHITECTURE.md` section 5. Round coordinates before building keys. The cache must be optional: the code works with `cache=None`.

## Fixtures and fakes
- `tests/fixtures/mapbox/{denver_slc,short_trip,no_route,one_alternative}.json`
- `tests/fixtures/open_meteo/{multi_point_winter,nulls,single_point}.json`
- Record with `scripts/record_fixtures.py` (needs keys, run only when asked). Strip tokens before saving.
- `providers/fakes.py`: `FakeRouting` (3 hand-made polylines with annotations) and `FakeWeather` (a deterministic function of lat, lon and time). Used by golden scenarios and `PROVIDERS=fake` local dev.

## Checklist
- [ ] lon,lat order is correct in the Mapbox URL
- [ ] Units are converted once, in the adapter, through `units.py`
- [ ] Chunking and parallelism are bounded by a semaphore
- [ ] Retries, timeouts and error mapping are tested with respx
- [ ] No real network in tests (pytest-socket)
- [ ] No token appears in logs, errors or fixtures
