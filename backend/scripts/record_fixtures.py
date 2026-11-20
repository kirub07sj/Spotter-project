"""Records real provider responses into planner/tests/fixtures, with tokens stripped.
Needs MAPBOX_TOKEN and network access. Run only when asked (CLAUDE.md):

    uv run --env-file ../.env python scripts/record_fixtures.py
"""

import json
import os
import sys
from pathlib import Path

import httpx

OUT = Path(__file__).resolve().parent.parent / "planner" / "tests" / "fixtures"
DIRECTIONS = "https://api.mapbox.com/directions/v5/mapbox/driving/"
GEOCODE = "https://api.mapbox.com/search/geocode/v6/forward"
METEO = os.environ.get("OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast")
ROUTE_PARAMS = {
    "geometries": "polyline6",
    "overview": "full",
    "annotations": "distance,duration",
    "steps": "false",
}
HOURLY = "wind_speed_10m,wind_gusts_10m,rain,showers,snowfall"


def save(rel: str, body: object, token: str) -> None:
    text = json.dumps(body, separators=(",", ":"))
    if token and token in text:
        sys.exit(f"refusing to write {rel}: it contains the token")
    (OUT / rel).write_text(text + "\n")
    print(f"wrote {rel} ({len(text) // 1024} KB)")  # noqa: T201


def main() -> None:
    token = os.environ.get("MAPBOX_TOKEN", "")
    if not token:
        sys.exit("MAPBOX_TOKEN is required")
    with httpx.Client(timeout=20) as c:

        def directions(path: str, alternatives: bool) -> object:
            params = {
                **ROUTE_PARAMS,
                "alternatives": str(alternatives).lower(),
                "access_token": token,
            }
            return c.get(DIRECTIONS + path, params=params).json()

        save(
            "mapbox/denver_slc.json", directions("-104.9903,39.7392;-111.8910,40.7608", True), token
        )
        save(
            "mapbox/one_alternative.json",
            directions("-104.9903,39.7392;-111.8910,40.7608", True),
            token,
        )
        save(
            "mapbox/via_two_legs.json",
            directions("-104.9903,39.7392;-108.2,39.3;-111.8910,40.7608", False),
            token,
        )
        save(
            "mapbox/short_trip.json",
            directions("-104.9903,39.7392;-105.2705,40.0150", False),
            token,
        )
        save("mapbox/no_route.json", directions("-104.9903,39.7392;-0.1276,51.5072", False), token)
        save(
            "mapbox/geocode_denver.json",
            c.get(
                GEOCODE,
                params={"q": "denver", "limit": 2, "country": "us,ca", "access_token": token},
            ).json(),
            token,
        )
        base = {"hourly": HOURLY, "timezone": "GMT", "timeformat": "unixtime", "forecast_hours": 24}
        save(
            "open_meteo/multi_point_winter.json",
            c.get(
                METEO,
                params={
                    **base,
                    "latitude": "39.74,41.31,39.06",
                    "longitude": "-104.99,-105.59,-108.55",
                },
            ).json(),
            token,
        )
        save(
            "open_meteo/single_point.json",
            c.get(
                METEO,
                params={**base, "latitude": "40.76", "longitude": "-111.89", "forecast_hours": 6},
            ).json(),
            token,
        )


if __name__ == "__main__":
    main()
