"""Writes synthetic provider fixtures in the exact response shape of Mapbox Directions v5,
Mapbox Geocoding v6 and Open-Meteo, for when real recordings aren't available.

    uv run python scripts/make_synthetic_fixtures.py

Real recordings (scripts/record_fixtures.py, needs keys) replace these files one for one.
Geometry follows real highway corridors through real towns, but it is not road-accurate."""

import itertools
import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polyline

OUT = Path(__file__).resolve().parent.parent / "planner" / "tests" / "fixtures"
R = 6_371_008.8

DENVER = (39.7392, -104.9903)
SLC = (40.7608, -111.8910)
BOULDER = (40.0150, -105.2705)
CHEYENNE = (41.1400, -104.8202)

I80 = [
    DENVER,
    (40.5853, -105.0844),
    (41.3114, -105.5911),
    (41.7911, -107.2387),
    (41.5875, -109.2029),
    (41.2683, -110.9632),
    (40.9, -111.5),
    SLC,
]
I70 = [
    DENVER,
    (39.6403, -106.3742),
    (39.5505, -107.3248),
    (39.0639, -108.5506),
    (38.9958, -110.1596),
    (39.5994, -110.8107),
    (40.2338, -111.6585),
    SLC,
]
US40 = [
    DENVER,
    (40.0, -105.8),
    (40.4850, -106.8317),
    (40.5153, -107.5464),
    (40.4555, -109.5287),
    (40.5069, -111.4132),
    SLC,
]


def hav(a: tuple[float, float], b: tuple[float, float]) -> float:
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def densify(waypoints: list[tuple[float, float]], step_m: float) -> list[tuple[float, float]]:
    out = [waypoints[0]]
    for a, b in itertools.pairwise(waypoints):
        n = max(int(hav(a, b) / step_m), 1)
        for i in range(1, n + 1):
            f = i / n
            wiggle = 0.004 * math.sin(i * 0.7) * (1 if i < n else 0)  # curves, not ruler lines
            out.append(
                (round(a[0] + (b[0] - a[0]) * f + wiggle, 6), round(a[1] + (b[1] - a[1]) * f, 6))
            )
    return out


def route(
    waypoints: list[tuple[float, float]],
    speeds_mps: list[float],
    summaries: list[str],
    legs_split: int | None = None,
) -> dict:
    coords = densify(waypoints, 1500)
    dist = [round(hav(a, b), 1) for a, b in itertools.pairwise(coords)]
    dur = [round(d / speeds_mps[i % len(speeds_mps)], 1) for i, d in enumerate(dist)]
    cut = legs_split or len(dist)
    legs = []
    for lo, hi, summary in ((0, cut, summaries[0]), (cut, len(dist), summaries[-1])):
        if hi > lo:
            legs.append(
                {
                    "summary": summary,
                    "weight": round(sum(dur[lo:hi]) * 1.1, 1),
                    "duration": round(sum(dur[lo:hi]), 1),
                    "distance": round(sum(dist[lo:hi]), 1),
                    "steps": [],
                    "via_waypoints": [],
                    "admins": [{"iso_3166_1": "US"}],
                    "annotation": {"distance": dist[lo:hi], "duration": dur[lo:hi]},
                }
            )
    return {
        "weight_name": "auto",
        "weight": round(sum(dur) * 1.1, 1),
        "duration": round(sum(dur), 1),
        "distance": round(sum(dist), 1),
        "legs": legs,
        "geometry": polyline.encode(coords, 6),
    }


def directions(routes: list[dict], stops: list[tuple[float, float]]) -> dict:
    return {
        "routes": routes,
        "waypoints": [{"distance": 3.2, "name": "", "location": [s[1], s[0]]} for s in stops],
        "code": "Ok",
        "uuid": "synthetic-fixture",
    }


def hourly_location(lat: float, lon: float, start: datetime, hours: int, kind: str) -> dict:
    times = [int((start + timedelta(hours=i)).timestamp()) for i in range(hours)]
    wind, gust, rain, showers, snow = [], [], [], [], []
    for i in range(hours):
        storm = math.exp(-(((i - 10) / 4) ** 2)) if kind == "winter" else 0.0
        wind.append(round(14 + 30 * storm + (lat - 39) * 2, 1))
        gust.append(round(25 + 62 * storm + (lat - 39) * 3, 1))
        rain.append(round(0.4 * storm if lat < 40 else 0.0, 2))
        showers.append(round(0.3 * storm if lat < 40 else 0.0, 2))
        snow.append(round(4.2 * storm if lat >= 40 else 0.0, 2))
    if kind == "nulls":
        for arr in (gust, snow):
            arr[3] = None
        rain[5] = None
    return {
        "latitude": round(lat * 4) / 4,
        "longitude": round(lon * 4) / 4,
        "generationtime_ms": 0.42,
        "utc_offset_seconds": 0,
        "timezone": "GMT",
        "timezone_abbreviation": "GMT",
        "elevation": 1609.0,
        "hourly_units": {
            "time": "unixtime",
            "wind_speed_10m": "km/h",
            "wind_gusts_10m": "km/h",
            "rain": "mm",
            "showers": "mm",
            "snowfall": "cm",
        },
        "hourly": {
            "time": times,
            "wind_speed_10m": wind,
            "wind_gusts_10m": gust,
            "rain": rain,
            "showers": showers,
            "snowfall": snow,
        },
    }


def write(rel: str, body: object) -> None:
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, separators=(",", ":")) + "\n")


def main() -> None:
    write(
        "mapbox/denver_slc.json",
        directions(
            [
                route(I80, [31.3, 29.0, 33.5], ["I 80, I 25"]),
                route(US40, [24.6, 22.0], ["US 40"]),
                route(I70, [29.5, 27.0, 31.0], ["I 70, US 6"]),
            ],
            [DENVER, SLC],
        ),
    )
    write(
        "mapbox/one_alternative.json",
        directions(
            [
                route(I80, [31.3, 29.0, 33.5], ["I 80, I 25"]),
                route([DENVER, (40.55, -105.06), *I80[2:]], [30.0, 28.5], ["US 287, I 80"]),
            ],
            [DENVER, SLC],
        ),
    )
    via = (39.3, -108.2)
    write(
        "mapbox/via_two_legs.json",
        directions(
            [
                route(
                    [DENVER, (39.5505, -107.3248), via, (39.6, -110.0), SLC],
                    [28.0, 26.0],
                    ["I 70", "US 6, I 15"],
                    legs_split=150,
                ),
            ],
            [DENVER, via, SLC],
        ),
    )
    write(
        "mapbox/short_trip.json",
        directions(
            [
                route([DENVER, (39.86, -105.10), BOULDER], [22.0, 26.0], ["US 36"]),
            ],
            [DENVER, BOULDER],
        ),
    )
    write(
        "mapbox/no_route.json",
        {"code": "NoRoute", "message": "No route found", "routes": [], "waypoints": []},
    )
    write(
        "mapbox/geocode_denver.json",
        {
            "type": "FeatureCollection",
            "attribution": "synthetic",
            "features": [
                {
                    "type": "Feature",
                    "id": "dXJuOm1ieHBsYzpBZm5sN0E",
                    "geometry": {"type": "Point", "coordinates": [-104.9903, 39.7392]},
                    "properties": {
                        "mapbox_id": "dXJuOm1ieHBsYzpBZm5sN0E",
                        "feature_type": "place",
                        "name": "Denver",
                        "place_formatted": "Colorado, United States",
                        "full_address": "Denver, Colorado, United States",
                    },
                },
                {
                    "type": "Feature",
                    "id": "dXJuOm1ieHBsYzpEZW5UWA",
                    "geometry": {"type": "Point", "coordinates": [-97.1331, 33.2148]},
                    "properties": {
                        "mapbox_id": "dXJuOm1ieHBsYzpEZW5UWA",
                        "feature_type": "place",
                        "name": "Denton",
                        "place_formatted": "Texas, United States",
                    },
                },
            ],
        },
    )
    start = datetime(2026, 11, 20, 13, tzinfo=UTC)
    write(
        "open_meteo/multi_point_winter.json",
        [
            hourly_location(39.74, -104.99, start, 24, "winter"),
            hourly_location(41.31, -105.59, start, 24, "winter"),
            hourly_location(39.06, -108.55, start, 24, "winter"),
        ],
    )
    write(
        "open_meteo/nulls.json",
        [
            hourly_location(41.79, -107.24, start, 12, "nulls"),
            hourly_location(41.59, -109.20, start, 12, "calm"),
        ],
    )
    write("open_meteo/single_point.json", hourly_location(40.76, -111.89, start, 6, "calm"))


if __name__ == "__main__":
    main()
