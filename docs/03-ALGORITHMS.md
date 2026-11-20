# 03. Algorithms

Every calculation the app performs, in the order it happens. The pseudocode is close to the real Python, so agents can implement it directly. Decision IDs (D-xx) point to `01-SPEC.md`.

**Domain units:** miles, seconds, mph, in/hr, lb, UTC-aware datetime. Internal geometry math uses meters and converts to miles at the end.

---

## 1. Units (`domain/units.py`)

```python
KMH_PER_MPH = 1.609344
MM_PER_IN   = 25.4
CM_PER_IN   = 2.54
M_PER_MI    = 1609.344
LB_PER_T    = 2204.62262

def kmh_to_mph(v): return v / KMH_PER_MPH
def mm_to_in(v):   return v / MM_PER_IN     # rain, showers
def cm_to_in(v):   return v / CM_PER_IN     # snowfall
def m_to_mi(v):    return v / M_PER_MI
```

Always request Open-Meteo in its defaults (km/h, mm, cm) and convert here. Its docs don't clearly say whether `precipitation_unit=inch` also changes `snowfall`, so we avoid relying on that.

---

## 2. Routes (`providers/mapbox_routing.py`)

**Request**
```
GET https://api.mapbox.com/directions/v5/mapbox/driving/{lon,lat};{lon,lat}
  ?alternatives=true
  &geometries=polyline6
  &overview=full
  &annotations=distance,duration
  &steps=false
  &access_token=...
  [&max_weight={gross_t}]          # only if MAPBOX_USE_MAX_WEIGHT
```
Note: Mapbox takes coordinates as **longitude, latitude**.

**Normalize each route into:**
```python
@dataclass(frozen=True, slots=True)
class RouteGeometry:
    coords: tuple[LatLon, ...]        # full resolution
    seg_dist_m: tuple[float, ...]     # len = len(coords) - 1, from annotations
    seg_dur_s: tuple[float, ...]      # len = len(coords) - 1, from annotations
    summary: str                      # legs[0].summary, e.g. "I 80, I 76"
```
If the annotations are missing or their lengths don't match, compute `seg_dist_m` with haversine and spread the route's total duration across segments in proportion to distance. Log a warning when this happens.

**Optional max_weight:** `gross_t = min(100, (load_lb + TRACTOR_TRAILER_TARE_LB) / LB_PER_T)`.

---

## 3. Getting 3 distinct routes (`domain/alternatives.py`) · D-13

Mapbox returns at most 2 alternatives. Fill the gap with via-points:

```python
def candidate_via_points(origin, dest):
    D = haversine_m(origin, dest)
    mid = midpoint(origin, dest)
    bearing = initial_bearing(origin, dest)
    for frac in (0.15, -0.15, 0.30, -0.30):
        yield destination_point(mid, bearing + 90, frac * D)   # perpendicular offset

def build_route_set(primary_routes, fetch_via):
    accepted = dedupe(primary_routes)                       # provider routes first
    fastest = min(r.duration_s for r in accepted)
    for via in candidate_via_points(o, d):
        if len(accepted) >= 3: break
        cand = fetch_via(o, via, d)                          # alternatives=false
        if cand is None: continue
        if cand.duration_s > 1.5 * fastest: continue         # unreasonable detour
        if any(overlap_ratio(cand, r) > 0.80 for r in accepted): continue
        accepted.append(cand.with_source("via"))
    return sorted(accepted, key=lambda r: r.duration_s)
```

Fetch the via candidates in parallel and then apply the filters in the fixed order above, so the result is deterministic.

**overlap_ratio(a, b):** sample `a` every 1 km. The ratio is the share of samples within 1.5 km of polyline `b`. Use shapely with an equirectangular projection centered on the corridor (accurate enough at this scale), and an `STRtree` on `b`'s segments.

Route IDs `A`, `B`, `C` are given by ascending duration. Labels come from `summary` ("via I 80"). If that's empty, use "Route A".

---

## 4. ETA with the truck speed cap (`domain/eta.py`) · D-07

```python
def capped_durations(seg_dist_m, seg_dur_s, cap_mph):
    if cap_mph <= 0: return seg_dur_s
    cap_mps = cap_mph * M_PER_MI / 3600
    return tuple(max(t, d / cap_mps) for d, t in zip(seg_dist_m, seg_dur_s))

def cumulative(xs):            # returns len(xs)+1, starting at 0.0
    out = [0.0]
    for x in xs: out.append(out[-1] + x)
    return out
```
`route.duration_s = cum_dur[-1]` after capping. `arrival = departure + duration`.

---

## 5. Checkpoints (`domain/sampling.py`) · D-06

```python
def checkpoint_miles(total_mi, interval_mi):
    miles = [0.0]
    m = interval_mi
    while m <= total_mi - 0.5:         # D-06: drop only if *less than* 0.5 mi before the end
        miles.append(m); m += interval_mi
    miles.append(total_mi)
    return miles

def locate(cum_dist_m, cum_dur_s, coords, target_m):
    i = bisect_right(cum_dist_m, target_m) - 1
    i = clamp(i, 0, len(coords) - 2)
    seg = cum_dist_m[i+1] - cum_dist_m[i]
    f = 0.0 if seg == 0 else (target_m - cum_dist_m[i]) / seg
    point = lerp_latlon(coords[i], coords[i+1], f)          # fine for segments < few km
    t = cum_dur_s[i] + f * (cum_dur_s[i+1] - cum_dur_s[i])
    return point, t

def sample(route, departure_utc, interval_mi):
    for idx, mi in enumerate(checkpoint_miles(route.distance_mi, interval_mi)):
        p, t = locate(..., mi * M_PER_MI)
        yield Checkpoint(index=idx, mile=mi, at=p, eta=departure_utc + timedelta(seconds=t))
```
Complexity: O(n + k log n) per route, where n is the number of coords and k the number of checkpoints.

---

## 6. Weather (`providers/open_meteo.py`, `domain/weather_lookup.py`) · D-04, D-05, D-08

**One batched fetch for all routes**
1. Collect the checkpoints of all routes. Round each to 2 decimal places (about 1 km) to get a dedupe key.
2. Time window: `start = floor_hour(departure)`, `end = ceil_hour(latest arrival) + 1h`.
3. Split the unique points into chunks of 100 (Open-Meteo documents no limit, so we stay conservative). Fetch the chunks in parallel.

```
GET {OPEN_METEO_BASE_URL}
  ?latitude=a,b,c&longitude=x,y,z
  &hourly=wind_speed_10m,wind_gusts_10m,rain,showers,snowfall
  &timezone=GMT&timeformat=unixtime
  &start_hour=2026-11-20T13:00&end_hour=2026-11-21T09:00
```
With several coordinates the response is a list, in the same order as the request.

**Bucket lookup (D-08)**
```python
def bucket_time(eta):                         # value at T covers (T-1h, T]
    floor = eta.replace(minute=0, second=0, microsecond=0)
    return floor if eta == floor else floor + timedelta(hours=1)

def sample_for(series, eta) -> WeatherSample:
    T = bucket_time(eta)
    i = series.index_of(T)                    # dict lookup by unix time
    return WeatherSample(
        wind_mph = kmh_to_mph(series.wind_speed_10m[i]),
        gust_mph = kmh_to_mph(series.wind_gusts_10m[i]),
        rain_in_hr = mm_to_in(series.rain[i] + series.showers[i]),
        snow_in_hr = cm_to_in(series.snowfall[i]),
        forecast_hour = T,
    )
```
Treat `null` values as missing. If any field needed for classification is missing, set the checkpoint's level to `UNKNOWN`. Leave its miles out of the stats and add the warning `WEATHER_GAPS`. Never assume Low.

---

## 7. Risk classification (`domain/risk.py`) · D-01 to D-03

```python
class Level(IntEnum):
    LOW = 0; MODERATE = 1; HIGH = 2; SEVERE = 3; NO_TRAVEL = 4

# lower bounds of MODERATE, HIGH, SEVERE (inclusive)
WIND_BANDS = (25.0, 35.0, 45.0); WIND_NO_TRAVEL_AT_OR_ABOVE = 55.0
RAIN_BANDS = (0.10, 0.25, 0.50); RAIN_NO_TRAVEL_ABOVE = 1.00
SNOW_BANDS = (0.5, 1.0, 2.0);    SNOW_NO_TRAVEL_ABOVE = 3.0

def band(v, bands):
    lvl = Level.LOW
    for i, b in enumerate(bands, start=1):
        if v >= b: lvl = Level(i)
    return lvl

def classify_wind(mph, load_lb) -> tuple[Level, bool]:      # (level, load_adjusted)
    if mph >= 55.0:                          return Level.NO_TRAVEL, False
    base = band(mph, WIND_BANDS)
    if 45.0 <= mph < 55.0 and load_lb > 30_000: return Level.NO_TRAVEL, True
    if 35.0 <= mph < 45.0 and load_lb > 40_000: return max(base, Level.SEVERE), True
    return base, False

def classify_rain(v): return Level.NO_TRAVEL if v > RAIN_NO_TRAVEL_ABOVE else band(v, RAIN_BANDS)
def classify_snow(v): return Level.NO_TRAVEL if v > SNOW_NO_TRAVEL_ABOVE else band(v, SNOW_BANDS)

def classify_checkpoint(ws: WeatherSample, load_lb, wind_metric) -> RiskResult:
    wind_v = ws.gust_mph if wind_metric == "gust" else ws.wind_mph
    w, adjusted = classify_wind(wind_v, load_lb)
    s = classify_snow(ws.snow_in_hr)
    r = classify_rain(ws.rain_in_hr)
    overall = max(w, s, r)
    dominant = next(name for name, l in (("wind", w), ("snow", s), ("rain", r)) if l == overall)
    return RiskResult(wind=w, rain=r, snow=s, overall=overall, dominant_factor=dominant, load_adjusted=adjusted)
```

**Required boundary tests** (table-driven, `test_risk_boundaries.py`):

| Input | Load | Expected |
|---|---|---|
| wind 24.99 | 0 | LOW |
| wind 25.0 | 0 | MODERATE |
| wind 34.99 | 0 | MODERATE |
| wind 35.0 | 40,000 | HIGH (not > 40k) |
| wind 35.0 | 40,001 | SEVERE, adjusted |
| wind 44.99 | 45,000 | SEVERE, adjusted |
| wind 45.0 | 30,000 | SEVERE (not > 30k) |
| wind 45.0 | 30,001 | NO_TRAVEL, adjusted |
| wind 54.99 | 0 | SEVERE |
| wind 55.0 | 0 | NO_TRAVEL, not adjusted |
| rain 0.0999 / 0.10 / 0.25 / 0.50 / 1.00 / 1.0001 | any | LOW / MOD / HIGH / SEVERE / SEVERE / NO_TRAVEL |
| snow 0.49 / 0.5 / 1.0 / 2.0 / 3.0 / 3.01 | any | LOW / MOD / HIGH / SEVERE / SEVERE / NO_TRAVEL |

**Property tests** (Hypothesis, `test_risk_properties.py`):
- Monotonic: raising any single input never lowers the overall level.
- Load monotonic: raising the load never lowers the level.
- The overall level is always >= each component level.

### 7.1 Continuous score for the heatmap (`risk.continuous_score`) · D-15

Maps a value onto [0, 4] so that `floor(score) == level` (with No Travel = 4.0):

```python
def piecewise(v, bands, nt_edge):
    edges = (0.0, *bands, nt_edge)                       # 5 edges -> 4 intervals
    if v >= nt_edge: return 4.0
    for k in range(4):
        lo, hi = edges[k], edges[k+1]
        if v < hi: return k + (v - lo) / (hi - lo) * 0.999
    return 4.0

def continuous_score(ws, load_lb, wind_metric):
    wv = ws.gust_mph if wind_metric == "gust" else ws.wind_mph
    w = piecewise(wv, WIND_BANDS, 55.0)
    lvl, _ = classify_wind(wv, load_lb)                  # load rules lift the floor
    w = max(w, float(lvl))
    r = piecewise(ws.rain_in_hr, RAIN_BANDS, 1.0 + 1e-9)
    s = piecewise(ws.snow_in_hr, SNOW_BANDS, 3.0 + 1e-9)
    return max(w, r, s)
```
Implement a numpy-vectorized version (`np.searchsorted` on the edges) for the heatmap grid. Test that the scalar and vectorized versions agree on 10,000 random inputs.

---

## 8. Mile attribution and stats (`domain/attribution.py`) · D-09, D-10

```python
def owned_intervals(miles):                     # miles sorted, first 0, last L
    L = miles[-1]; out = []
    for i, m in enumerate(miles):
        left  = 0.0 if i == 0 else (miles[i-1] + m) / 2
        right = L   if i == len(miles)-1 else (m + miles[i+1]) / 2
        out.append((left, right))
    return out                                  # sum(right-left) == L exactly

def route_stats(checkpoints):
    by_level = defaultdict(float); weighted = 0.0; known = 0.0
    for cp in checkpoints:
        miles = cp.right - cp.left
        if cp.level is Level.UNKNOWN: continue
        by_level[cp.level] += miles
        weighted += miles * int(cp.level); known += miles
    avg = weighted / known if known else 0.0
    return RouteStats(miles_by_level=by_level, avg_risk=avg, max_level=max(...))
```

**Risk segments for the map:** merge neighbouring intervals that share a level into runs `(from_mi, to_mi, level)`. Then slice the full-resolution geometry at those mile marks (reusing `locate`), simplify each slice, and encode it as polyline6.

**Tests:** owned miles add up to the route length (property test), a single checkpoint owns everything, and two checkpoints split at the midpoint.

---

## 9. Ranking and recommendation (`domain/ranking.py`) · D-11, D-12

```python
def ranking_key(r):
    s = r.stats.miles_by_level
    return (
        round(s[NO_TRAVEL], 1),
        round(s[SEVERE], 1),
        round(s[HIGH], 1),
        round(r.stats.avg_risk, 2),
        round(r.duration_s / 60),
    )

def recommend(routes):
    ranked = sorted(routes, key=ranking_key)
    best = ranked[0]
    status = "NO_SAFE_ROUTE" if best.stats.miles_by_level[NO_TRAVEL] > 0 else "OK"
    reasons = [explain(best, other) for other in ranked[1:]]
    return Recommendation(route_id=best.id, status=status, reasons=reasons), ranked
```

**explain(best, other):** find the first key position where they differ and describe it in plain words:
- `"Chosen over B: 25.0 fewer Severe miles"`
- `"Chosen over C: same Severe and High miles, lower average risk (0.42 vs 0.61)"`
- `"Chosen over B: same risk profile, 18 min faster"`
- If every key is equal: `"Tied with B on every criterion; listed first by route ID"`. In that case, add `id` as the final tiebreaker so the result is deterministic.

Note for the README and Loom: following the brief, the order is strict. One fewer Severe mile beats a 2 hour longer drive. The reasons text makes that trade-off visible to the driver.

**Golden scenario tests** (`test_golden_scenarios.py`): 3 fake routes with hand-written weather, where the expected winner and reasons are written by hand. Cover:
1. Severe miles decide
2. Severe is tied, High decides
3. Severe and High are tied, average risk decides
4. Everything is tied, duration decides
5. Every route has No Travel, so status is NO_SAFE_ROUTE
6. The load rule flips the winner (same weather, 35,000 lb vs 45,000 lb)

---

## 10. Heatmap grid (`domain/heatmap.py`) · D-14 to D-16

```python
def build_grid(route_geoms, corridor_km, max_points):
    corridor = union(buffer(line, corridor_km) for line in route_geoms)   # projected meters
    minx, miny, maxx, maxy = bbox_latlon(corridor)
    area_deg2 = (maxx - minx) * (maxy - miny)
    step = max(0.08, sqrt(area_deg2 / (max_points * 2.2)))   # ~45% of bbox cells fall in a corridor
    lats = arange(miny - step, maxy + step, step)
    lons = arange(minx - step, maxx + step, step)
    mask = cells_within(corridor.buffer(step_m), lats, lons)  # one ring of padding
    while mask.sum() > max_points:                           # guarantee the budget
        step *= 1.15; ... rebuild
    return Grid(lat0=lats[0], lon0=lons[0], dlat=step, dlon=step, rows, cols), mask
```

**Weather for the grid:** one batched Open-Meteo request (chunked by 100) for the masked points, with `start_hour = ceil_to_hour(departure)` (D-08) and `end_hour = start_hour + 48h`. That gives 49 hourly values. Frame labels are the exact departure plus 0 to 48 hours (D-14), including departures between whole hours. Scenario deltas use the forecast bucket time, matching checkpoints.

**Scoring:** build an array of shape `(49, rows, cols)`, fill in the vectorized `continuous_score`, and set unmasked cells to 255.

**Encoding:** `uint8 = floor(score * 50)` (0 to 200), with 255 meaning no data. Floor, not round: rounding lifts the top of a band (2.999 to 150, which decodes as 3.0) into the next level and breaks D-15. Base64-encode it. For 49 × 30 × 60 that's about 88 KB raw, or about 30 KB gzipped.

---

## 11. Heatmap rendering (frontend worker) · see `04-UI-DESIGN.md` section 5

```ts
// heatmap.worker.ts
for (let h = 0; h < hours; h++) {
  const img = new ImageData(W, H);                       // W,H ~ 4-6x grid size, in Web Mercator space
  for (let py = 0; py < H; py++) {
    const lat = mercatorYToLat(yTop + py * dy);          // sample in Mercator so it aligns with the map
    const gy = (lat - lat0) / dlat;
    for (let px = 0; px < W; px++) {
      const gx = (lonLeft + px * dx - lon0) / dlon;
      const s = bilinear(scores, h, gx, gy);             // skips 255 cells and renormalizes the weights
      if (s < 0) continue;                               // transparent
      const c = LUT[Math.round(s * 50)];                 // 201-entry RGBA lookup table
      img.data.set(c, (py * W + px) * 4);
    }
  }
  bitmaps[h] = await createImageBitmap(img);
}
postMessage({ bitmaps }, bitmaps);                       // transferable, zero-copy
```
Render the current hour first, then the rest, and post progress messages so the slider can be used early.

---

## 12. Simulated scenarios (`domain/scenarios.py`) · D-20

A scenario is a pure function `(lat, lon, t) -> WeatherDelta` that is added to the real values before classification. Example, `winter_storm`: a Gaussian blob centered on the midpoint of route A, radius 120 km, peak snow 2.5 in/hr and gusts 50 mph. It moves east at 30 km/h over the 48 hours. Because one function feeds both checkpoints and heatmap, they stay consistent. Seeded and deterministic.

---

## 13. Edge cases checklist

- [ ] Origin equals destination, so return 400
- [ ] A route under one interval long gets 2 checkpoints (origin and destination)
- [ ] Zero-length segments in the geometry (avoid dividing by zero in `locate`)
- [ ] A via-point snaps somewhere unreachable, so Mapbox returns `NoRoute` for it. Skip it.
- [ ] A trip crosses midnight or a DST change. Everything is UTC, so this is a non-issue. Test it anyway.
- [ ] Departure in the past (within 1h). The past hour is not available, so clamp the bucket to the current hour.
- [ ] Open-Meteo returns `null` for some hours, leading to `UNKNOWN` and a warning
- [ ] All 3 routes identical in risk and duration, so the tiebreak is by ID
- [ ] Very long route (3,000 mi at a 10 mi interval gives about 900 checkpoints). The chunked fetch must stay under 3 s.
