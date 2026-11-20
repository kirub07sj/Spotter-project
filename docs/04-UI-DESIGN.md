# 04. UI Design and Map Performance

40% of the grade is UI, map and heatmap smoothness. This doc defines what the user sees and how it stays fast.

## 1. Design principles

1. **Answer first.** The recommendation banner is the first thing the eye lands on: which route, and why, in one line.
2. **Color never carries meaning alone.** Every risk color comes with a text label or icon.
3. **The map is the workspace.** The panels support the map and never cover the selected route.
4. **Nothing janky.** Dragging the slider, hovering and switching routes must feel instant. If something takes time, show progress where the result will appear.
5. **Honest.** Assumptions, simulated weather and low-confidence forecasts are always visible.

## 2. Layout

**Desktop (>= 1024 px)**
```
┌───────────────┬────────────────────────────────────────────────┐
│ PLAN FORM     │                                                │
│ origin        │                    MAP                         │
│ destination   │   routes, risk segments, checkpoints,          │
│ departure     │   heatmap raster, truck markers                │
│ load (lb)     │                                     [legend]   │
│ interval 10|25|50                                   [layers]   │
│ [Plan route]  │                                                │
├───────────────┤                                                │
│ RECOMMENDATION│                                                │
│ banner        │                                                │
├───────────────┤ ┌────────────────────────────────────────────┐ │
│ ROUTE CARDS   │ │ ▶  ──●────────────────  +12h · Thu 14:00   │ │
│ A  B  C       │ │    forecast timeline 0-48h with ETA ticks  │ │
├───────────────┤ └────────────────────────────────────────────┘ │
│ CHECKPOINTS   │                                                │
│ table (sel.)  │                                                │
└───────────────┴────────────────────────────────────────────────┘
  400 px fixed            flexible
```
**Tablet and mobile (< 1024 px):** full-screen map. The form becomes a collapsible top sheet. Route cards and checkpoints go in a draggable bottom sheet with 3 snap points (peek, half, full). The slider is pinned above the bottom sheet.

## 3. Components

| Component | Contents | Notes |
|---|---|---|
| `PlanForm` | Geocoder inputs (debounced 250 ms, min 3 chars, aborts stale requests), datetime-local, load with thousands separator, segmented control for the interval | react-hook-form + zod mirroring D-17. Submit disabled while invalid or loading |
| `RecommendationBanner` | Route letter + label, status chip, first reason, "Why?" expands all reasons | Red variant for `NO_SAFE_ROUTE` |
| `RouteCard` | Letter, label, duration, distance, arrival time, stacked bar of miles by level, avg risk, max level chip, "Recommended" badge | Click or Enter selects. Hover highlights the route on the map |
| `RiskBar` | Horizontal stacked bar (Low to No Travel) proportional to miles, with tooltip values | The same component sits in cards and in the legend |
| `CheckpointTable` | Mile, ETA, wind/gust, rain, snow, level chip, dominant factor icon, load-adjusted marker | Virtualized when over 60 rows. Row hover highlights the map marker and the other way round |
| `MapView` | MapLibre basemap + deck.gl overlay (interleaved) | Lazy-loaded chunk |
| `ForecastSlider` | Play/pause, range input 0-48 with step 0.05, hour ticks, ETA ticks for the selected route, label "+12h · Thu 14:00" | Keyboard: arrows ±1h, Shift+arrows ±6h, Space to play |
| `Legend` | Risk scale (discrete chips + continuous gradient), route identity colors | Collapsible |
| `LayerToggles` | Heatmap on/off, heatmap opacity, show all routes, show checkpoints | |
| `AssumptionsFooter` | Wind metric, speed cap, HOS off, data sources, scenario badge | Always visible, small text |

## 4. Visual system

**Risk palette** (one source: `lib/risk.ts`)

| Level | Color | Label | Icon |
|---|---|---|---|
| LOW | `#2E9E5B` | Low | ● |
| MODERATE | `#E3B505` | Moderate | ▲ |
| HIGH | `#F08A24` | High | ◆ |
| SEVERE | `#D7263D` | Severe | ■ |
| NO_TRAVEL | `#5B1A8B` | No Travel | ✕ |
| UNKNOWN | `#9AA0A6` | No data | ? |

**Route identity colors** (these must not look like risk colors): A `#2563EB` (blue), B `#0891B2` (cyan), C `#64748B` (slate).

**Heatmap gradient:** continuous over score 0 to 4 using the same hues. Alpha rises with risk, so calm areas barely tint the map: alpha 0.10 at score 0, 0.35 at 1, 0.60 at 2, 0.75 at 3 and above.

**Typography:** Inter or the system UI font. Tabular numerals (`font-variant-numeric: tabular-nums`) for every number, so values don't jitter while the slider moves.

**Units:** mi, mph, in/hr, lb. Durations as "8h 06m". Times as "Thu 14:20 MST".

## 5. Map layers (bottom to top)

| # | Layer | Type | Data | Updates on slider? |
|---|---|---|---|---|
| 1 | Basemap | MapLibre style (light, muted) | Vector tiles | no |
| 2 | Heatmap (current hour) | deck `BitmapLayer` | worker ImageBitmap | `image` prop swap only |
| 3 | Heatmap (next hour) | deck `BitmapLayer` | worker ImageBitmap | `image` + `opacity` (crossfade) |
| 4 | Basemap labels | MapLibre symbol layers | | no (deck layers go in with `beforeId` of the first symbol layer, so labels stay readable) |
| 5 | Unselected routes | deck `PathLayer` | decoded polylines | no |
| 6 | Selected route casing | deck `PathLayer` | | no |
| 7 | Selected route risk segments | deck `PathLayer` | `risk_segments` | no |
| 8 | Checkpoints | deck `ScatterplotLayer` (pickable) | all checkpoints of the selected route | `getLineWidth` via `updateTriggers` to emphasize the checkpoint nearest the slider time |
| 9 | Truck markers | deck `IconLayer` | position at slider time, per route | yes (one small array) |
| 10 | Origin and destination pins | deck `IconLayer` | | no |

**Tooltips:** deck `getTooltip` for checkpoints shows mile, ETA, gust, sustained wind, rain, snow, the level per condition, overall level, and a "load rule applied" line when it applies.

**Camera:** `fitBounds` on all routes with padding that accounts for the sidebar (left 420 px) and the slider (bottom 120 px). It animates only on a new plan, never on slider moves.

## 6. Heatmap rendering pipeline

1. `POST /heatmaps` starts as soon as the plan arrives (TanStack Query, keyed by plan_id).
2. The response is posted to `heatmap.worker.ts` as a transferable `ArrayBuffer`.
3. The worker decodes the data and builds a 201-entry RGBA LUT. It renders the **current hour first**, then the remaining 48 outward from the current hour, each in Web Mercator pixel space at about 5x grid resolution, bilinear, transparent outside the mask. Each is turned into an `ImageBitmap`.
4. The worker posts each bitmap as soon as it's ready (transferable). The main thread keeps `bitmaps: (ImageBitmap | undefined)[49]`.
5. Slider value `h` (float): `base = floor(h)`, `f = h - base`. Layer 2 gets `bitmaps[base]` at opacity `1 - f`, and layer 3 gets `bitmaps[base+1]` at opacity `f`. That's a smooth crossfade with no recompute.
6. If a bitmap hasn't arrived yet, show the nearest available one and a small "rendering 32/49" chip.

Memory check: 300 × 200 px × 4 bytes × 49 is about 12 MB of GPU textures. That's fine. Release the bitmaps (`bitmap.close()`) when a new plan replaces them.

## 7. State and rendering rules (frontend performance)

- **Server state:** TanStack Query. `usePlan(inputs)` and `useHeatmap(planId)`. `staleTime` 5 min. No refetch on window focus.
- **UI state:** a zustand store with `selectedRouteId`, `hour`, `playing`, `heatmapVisible`, `heatmapOpacity`, `hoveredCheckpoint`.
- **Slider isolation:** only `ForecastSlider` and `MapView` subscribe to `hour`, using fine-grained selectors. Route cards and the table must not re-render when `hour` changes. Verify with React DevTools "Highlight updates".
- **Memoize layer data:** decode polylines once per plan (`useMemo` on plan_id). Layers are rebuilt every frame, but they receive the same data references, and deck.gl diffs props cheaply. Use `updateTriggers` only for accessors that depend on `hour`.
- **Playback:** `requestAnimationFrame` loop that advances `hour` by `elapsed_ms / 1000 * 2` (2 forecast hours per second) and stops at 48.
- **Truck position at hour h:** for each route, binary search the cumulative-time array (sent with the plan as `cum_time_s` per simplified vertex) and interpolate. This is O(log n) per frame per route.
- **Geocoder:** debounce, `AbortController` per keystroke, cache results in a query cache.
- **Bundle:** lazy-load the map chunk (MapLibre + deck.gl) with `React.lazy` while the form renders. Target initial JS < 250 KB gzipped, map chunk < 450 KB gzipped.

## 8. Performance budget (measured in QA)

| Metric | Target |
|---|---|
| Time to first route render after submit (warm cache) | < 1.5 s |
| Same, cold cache | < 3.5 s |
| Heatmap first hour visible after plan render | < 2 s |
| All 49 bitmaps ready | < 4 s on a mid-range laptop |
| Slider drag | 60 fps, no long tasks over 50 ms (Performance panel) |
| Route hover and select | < 16 ms to respond |
| Lighthouse performance (desktop) | >= 85 |

## 9. States

| State | Behaviour |
|---|---|
| Empty (first load) | Map centered on the continental US. Form focused. Short hint: "Enter a trip to compare 3 routes by weather risk." |
| Loading plan | Submit button spinner. Skeletons for the banner and cards. The map keeps its current view |
| Plan ready, heatmap loading | Routes and cards are interactive. The slider is shown but disabled, with "Loading forecast…" |
| Partial (fewer than 3 routes) | Cards for what exists, plus an info note from `warnings` |
| No safe route | Red banner, No Travel segments drawn with a dashed purple overlay |
| Weather gaps | Grey "No data" checkpoints, with a warning chip in the banner |
| Error | Inline message near the form, mapped from the error `code`, plus a retry button. The form keeps its inputs |
| Simulated weather | Persistent amber badge "Simulated weather · winter storm" in the banner and the footer |

## 10. Accessibility

- All interactive elements reachable by keyboard, with a visible focus ring.
- The slider is a native `<input type="range">` with `aria-valuetext="Plus 12 hours, Thursday 2 PM"`.
- Route cards are `role="radio"` in a `radiogroup`.
- Text contrast >= 4.5:1. Risk chips use dark text on light tints, or white on the darkest two levels.
- Respect `prefers-reduced-motion`: disable autoplay and the camera fly animation.
- The checkpoint table is a real `<table>` with headers, so a screen reader can reach the same data as the map.
