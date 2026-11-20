---
name: map-performance
description: Use when building or changing the map view, deck.gl layers, route and checkpoint rendering, the heatmap worker and bitmaps, the 0-48h forecast slider, playback, truck markers, or anything affecting frontend rendering performance.
---

# Map and Heatmap Performance

This is the 40% "UI, map and heatmap smoothness" part of the grade.

## Before you start
Read `docs/04-UI-DESIGN.md` sections 5 to 8 and `docs/03-ALGORITHMS.md` sections 10 and 11.

## Architecture in one picture
```
plan JSON ──decode once (useMemo by plan_id)──▶ deck layers (routes, segments, checkpoints)
heatmap JSON ──transfer──▶ heatmap.worker ──ImageBitmap x49 (transfer)──▶ bitmaps[]
slider hour (zustand) ──▶ MapView only: BitmapLayer image/opacity, truck positions
```

## Hard rules
1. **No network and no heavy compute on slider change.** The slider changes the `image`, `opacity` and truck-position props. Nothing else.
2. **Only `ForecastSlider` and `MapView` subscribe to `hour`.** Use narrow zustand selectors. Route cards and the checkpoint table must not re-render while dragging.
3. **Decode polylines once per plan.** Keep decoded arrays in `useMemo` keyed by `plan_id`, never in state that changes often.
4. **Use deck.gl `BitmapLayer`, not `HeatmapLayer`.** HeatmapLayer aggregates point density. Our data is a field of values.
5. **Draw rasters in Web Mercator space** inside the worker (sample lat by inverse Mercator per pixel row). Otherwise a lat/lon raster drifts against the basemap over large spans.
6. **Keep labels on top:** add deck layers interleaved with `beforeId` set to the first symbol layer of the style.
7. **Crossfade between hours** with two BitmapLayers (`1 - f` and `f` opacity). The slider step is 0.05.
8. **Release memory:** call `bitmap.close()` on all old bitmaps when a new plan arrives. Terminate and recreate the worker if a plan is replaced mid-render.

## Worker protocol (typed)
```ts
type ToWorker   = { type: 'render'; planId: string; grid: Grid; scores: ArrayBuffer; mask: ArrayBuffer; hours: number; startHour: number; size: { w: number; h: number } };
type FromWorker = { type: 'bitmap'; planId: string; hour: number; bitmap: ImageBitmap }
                | { type: 'done'; planId: string }
                | { type: 'error'; planId: string; message: string };
```
Ignore messages whose `planId` isn't the current one. Render order: start hour first, then outward (h+1, h-1, h+2…).

## Truck markers
The plan gives `cum_time_s` per simplified vertex. At slider time `t = hour * 3600`, binary search, then interpolate between the two vertices. Hide the marker before departure and after arrival, or pin it to the endpoint with reduced opacity.

## Measuring (do this, don't guess)
1. Chrome Performance panel: record 5 s of slider drag. Pass means no long task over 50 ms and frames around 16 ms.
2. React DevTools Profiler with "Highlight updates": only the slider and map light up during a drag.
3. `performance.mark` around the worker render. All 49 bitmaps under 4 s.
4. `pnpm build && npx vite-bundle-visualizer`: the map chunk is lazy, and the initial chunk is under 250 KB gzipped.

## Common mistakes
- Making new data arrays inside the render function every frame, so deck.gl re-uploads buffers.
- Putting `hour` in a React context that wraps the whole app.
- Calling `fitBounds` in an effect that depends on `hour` or the selected route.
- Using `setState` per worker bitmap without batching. Collect them in a ref and bump one version counter per animation frame.
- Forgetting `pickable: true` and `autoHighlight` on checkpoints, so tooltips don't work.
