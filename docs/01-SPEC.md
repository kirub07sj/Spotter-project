# 01. Specification and Decisions

This file is the source of truth for behaviour. The original brief is reproduced in section 1. Section 2 resolves every ambiguity in it. If code and this file disagree, the code is wrong.

---

## 1. Original requirements

Build a React + Django web app that helps a truck driver choose the safest route based on weather, load weight and travel time.

**Inputs**
- Origin and destination
- Departure date and time
- Load weight

**The app must**
- R1. Generate 3 route options using a routing API
- R2. Sample weather every 10 / 25 / 50 miles, using the truck's estimated arrival time at each checkpoint
- R3. Calculate weather risk using the risk and load rules below
- R4. Recommend the best route, balancing weather risk and travel time
- R5. Show all routes, checkpoints, risk levels, ETAs and route summaries on a map
- R6. Show a weather heatmap along the trip corridor with a 0 to 48 hour forecast slider

Third-party APIs are allowed for routing, geocoding and weather. No routing engine needs to be built.

**Risk rules (per checkpoint)**

| Condition | Low | Moderate | High | Severe | No Travel |
|---|---|---|---|---|---|
| Wind | < 25 mph | 25-34 | 35-44 | 45-54 | >= 55 mph |
| Rain | < 0.10 in/hr | 0.10-0.25 | 0.25-0.50 | 0.50-1.00 | > 1.00 |
| Snow | < 0.5 in/hr | 0.5-1.0 | 1.0-2.0 | 2.0-3.0 | > 3.0 |

**Load rules**
- Wind >= 55 mph means No Travel for any load
- Wind 45-54 mph with load > 30,000 lb means No Travel
- Wind 35-44 mph with load > 40,000 lb means Severe

**Route recommendation, in priority order**
1. Fewest Severe miles
2. Fewest High miles
3. Lowest average risk
4. Shortest travel time

**Deliverables:** GitHub repo, hosted app, 5 to 10 minute Loom walkthrough.
**Evaluation:** 40% logic, 40% UI/map/heatmap smoothness and performance, 15% code quality, 5% docs and walkthrough. Prioritize correctness and clarity over extra features.

---

## 2. Decisions log

Status values: `ACCEPTED`, `PROPOSED` (needs a human), `SUPERSEDED`.

### D-01 Threshold boundaries · ACCEPTED
The brief's ranges overlap at the edges (0.25 is listed under both Moderate and High). Readings are floats, so we use half-open bands with an **inclusive lower bound**. The No Travel rules follow the brief literally.

| Condition | Low | Moderate | High | Severe | No Travel |
|---|---|---|---|---|---|
| Wind (mph) | v < 25 | 25 <= v < 35 | 35 <= v < 45 | 45 <= v < 55 | v >= 55 |
| Rain (in/hr) | v < 0.10 | 0.10 <= v < 0.25 | 0.25 <= v < 0.50 | 0.50 <= v <= 1.00 | v > 1.00 |
| Snow (in/hr) | v < 0.5 | 0.5 <= v < 1.0 | 1.0 <= v < 2.0 | 2.0 <= v <= 3.0 | v > 3.0 |

Why: "25-34 mph" written with integers means [25, 35) for continuous values. The Severe band for rain and snow includes its top value because the brief says No Travel is strictly "> 1.00" and "> 3.0".

### D-02 Overall checkpoint level · ACCEPTED
`overall = max(wind_level_after_load_rules, rain_level, snow_level)`. The condition that produced the max is stored as `dominant_factor` for the UI. If there's a tie, the order of preference is wind, then snow, then rain.

### D-03 Load rules apply to wind only · ACCEPTED
The load rules only mention wind, so they only change the wind level. "Load weight" is the cargo weight the user enters, in pounds. Comparisons are strict: `> 30,000` and `> 40,000`. A load of exactly 30,000 lb is not affected.

### D-04 Wind metric · ACCEPTED
Classify using **wind gusts at 10 m** (`wind_gusts_10m`). Sustained wind is shown alongside it in tooltips.
Why: blow-over risk for high-profile vehicles comes from gusts, and the brief is about the safest route. This can be changed with the `RISK_WIND_METRIC=gust|sustained` setting, and the active value is returned in `assumptions` and shown in the UI footer.

### D-05 Rain and snow variables · ACCEPTED
- Rain rate = `rain + showers` (liquid only, inches over the hour)
- Snow rate = `snowfall` (fresh snow depth, inches over the hour)
- `precipitation` is not used for rain, because it includes the water equivalent of snow and would count snow twice.

### D-06 Sampling interval · ACCEPTED
"10 / 25 / 50 miles" is read as a **user-selected interval**, defaulting to 25. Checkpoints sit at mile 0 (origin), N, 2N and so on, plus the destination. If the last regular checkpoint falls less than 0.5 mile before the destination, it's dropped and the destination is used instead, so there are no duplicate points.

### D-07 ETA model · ACCEPTED
- ETAs come from the routing provider's per-segment durations, accumulated from the departure time.
- **Truck speed cap:** no segment may be driven faster than `TRUCK_MAX_SPEED_MPH` (default 65). Car routing engines assume car speeds, and trucks are slower on highways. Setting it to 0 disables the cap.
- Hours-of-service breaks are **not modelled** by default (see Stretch S-02). The UI says this in the assumptions footer.

### D-08 Weather time lookup · ACCEPTED
Open-Meteo's hourly rain, showers, snowfall and gusts are totals or maxima over the **preceding hour**. A value stamped `T` covers `(T - 1h, T]`. For a checkpoint ETA `t`, use the bucket stamped `ceil_to_hour(t)`. If `t` is exactly on the hour, use `t`. Sustained wind (display only) uses the same bucket.

### D-09 Mile attribution · ACCEPTED
Each checkpoint "owns" the road from the midpoint with its previous checkpoint to the midpoint with its next one. The first and last checkpoints own up to the route ends. Owned miles add up exactly to the route length. A stretch's level is its checkpoint's overall level.

### D-10 Average risk · ACCEPTED
Distance-weighted mean of the level index (Low=0, Moderate=1, High=2, Severe=3, No Travel=4) over the owned miles. Range 0.00 to 4.00.

### D-11 Ranking key · ACCEPTED
Routes are sorted ascending, lexicographically, by:

```
( no_travel_miles, severe_miles, high_miles, avg_risk, duration_s )
```

No Travel miles come first even though the brief doesn't list them, because a route with No Travel road can't be "safer" than one with only Severe road. Miles are rounded to 0.1, avg risk to 0.01, and duration to whole minutes before comparing, so floating-point noise doesn't decide the result.

### D-12 No safe route · ACCEPTED
If the top-ranked route has any No Travel miles, recommendation status is `NO_SAFE_ROUTE`. The UI shows a red banner ("No route is safe to start at this time") but still highlights the least-bad route, with its No Travel stretches clearly marked.

### D-13 Fewer than 3 provider routes · ACCEPTED
Mapbox returns at most 2 alternatives and sometimes none. When fewer than 3 distinct routes come back, generate more using the via-point method in `03-ALGORITHMS.md` section 3. If 3 distinct routes still can't be found, return what exists and add the warning `ONLY_N_DISTINCT_ROUTES`. Never return near-duplicates just to reach 3.

### D-14 Heatmap time axis · ACCEPTED
The slider runs from **departure time + 0h to departure + 48h**, in hourly steps, with smooth blending between hours. Labels show both the offset and the clock time ("+12h · Thu 14:00"). The checkpoint markers and the truck marker sync to the slider time.
Why: the driver cares about weather at the time they'll be on the road. If departure is now, this is the same as a "from now" reading.

### D-15 Heatmap metric · ACCEPTED
Each grid cell shows a **continuous risk score** from 0 to 4. It's computed with the same thresholds and the same load rules as checkpoints (see `03-ALGORITHMS.md` section 7). So the heatmap and the checkpoints never disagree about a level.

### D-16 Corridor · ACCEPTED
Corridor = union of all route lines buffered by `HEATMAP_CORRIDOR_KM` (default 40 km). Grid points are kept only inside the corridor plus one ring of cells around it (for smooth edges).

### D-17 Input validation · ACCEPTED
- Load: integer, 1 to 80,000 lb
- Departure: from now minus 1 hour to now plus 7 days (forecast skill drops quickly after that)
- Interval: one of 10, 25, 50
- Origin and destination must be different, and the route must be under 3,000 miles

### D-18 Forecast confidence · ACCEPTED
Checkpoints with an ETA more than 72 hours from *now* are flagged `low_confidence: true` and shown with a dashed outline.

### D-19 Time display · ACCEPTED
The backend uses UTC only. The frontend shows times in the browser's time zone with the zone abbreviation (for example "Thu 14:20 MST").

### D-20 Simulated weather scenario · ACCEPTED
Real weather is often calm, which makes the logic impossible to demo. `scenario=winter_storm|high_wind` (query param, off by default) overlays synthetic weather fields on top of the real forecast. The UI shows a persistent "Simulated weather" badge whenever a scenario is active. Scenarios are only for the walkthrough and tests.

---

## 3. Traceability

Each requirement maps to code and the tests that prove it.

| Req | Implemented in | Proven by |
|---|---|---|
| R1 three routes | `providers/mapbox_routing.py`, `domain/alternatives.py` | `test_alternatives.py`, `test_mapbox_adapter.py` |
| R2 checkpoints with ETA-timed weather | `domain/sampling.py`, `domain/weather_lookup.py`, `providers/open_meteo.py` | `test_sampling.py`, `test_weather_lookup.py` |
| R3 risk and load rules | `domain/risk.py` | `test_risk_boundaries.py`, `test_risk_properties.py` |
| R4 recommendation | `domain/attribution.py`, `domain/ranking.py` | `test_attribution.py`, `test_ranking.py`, `test_golden_scenarios.py` |
| R5 map with routes, checkpoints, ETAs, summaries | `features/map`, `features/routes` | component tests, manual QA list in `06-DELIVERY.md` |
| R6 heatmap with 0-48h slider | `domain/heatmap.py`, `features/heatmap` | `test_heatmap_grid.py`, worker unit tests, perf check in QA list |

---

## 4. Out of scope

- Building a routing engine
- User accounts, saved trips, persistence
- Real truck restrictions (bridge heights, hazmat), apart from the optional Mapbox `max_weight`
- Mobile apps

## 5. Stretch (only after M7 is otherwise complete)

- S-01 Suggest a safer departure time: re-score the routes for departure offsets of +1h to +24h using weather already fetched, and show the earliest safe slot
- S-02 Hours-of-service mode: insert a 30 minute break after 8 hours of driving and a 10 hour rest after 11 hours, which shifts ETAs
- S-03 Shareable URL: encode the inputs in the query string
- S-04 Per-checkpoint weather sparkline in the tooltip
