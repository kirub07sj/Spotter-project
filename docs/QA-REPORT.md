# Final QA report (docs/06 §4)

Run on 2026-11-20 against commit `M7`. The environment matters for reading these results:

- **No network to Mapbox, Open-Meteo or the Carto basemap**, and no `MAPBOX_TOKEN`. Every run
  used `PROVIDERS=fake` (deterministic routes and weather with the same contract) and the
  map's plain fallback style.
- **No GPU.** The browser was headless Chromium 1243 with SwiftShader, which runs WebGL on the
  CPU. GPU-bound numbers here are pessimistic, and they are marked where they matter.
- The production stack was used: gunicorn + UvicornWorker with `config.settings.prod`, and
  `vite build` served by `vite preview`, cross-origin with CORS.

Legend: **PASS**; **FAIL**; **NOT VERIFIED** (can't be checked in this environment).

## Requirements

| Item | Result | Evidence |
|---|---|---|
| R1: 3 routes for a long trip; warning when fewer than 3 | PASS (fake) / NOT VERIFIED (Mapbox) | Fake routing returns 2 routes, so the via-point fallback adds the 3rd. `test_three_routes_with_via_fallback_and_full_contract` and `test_fewer_than_three_routes_warns`. The Mapbox adapter is tested against synthetic fixtures only |
| R2: interval 10/25/50 changes the checkpoint count; ETAs increase | PASS | `test_interval_changes_checkpoint_count`; ETAs checked as monotonic in the contract test |
| R3: boundary values give the expected levels through the API | PASS | `test_boundaries_through_api.py`: 36 cases (every wind, rain, snow and load edge) through `POST /plans` |
| R4: banner reasons match card stats; NO_SAFE_ROUTE renders | PASS | 6 golden scenarios through the API compare the exact reasons text, order and stats. The NO_SAFE_ROUTE banner is covered by a component test and a screenshot |
| R5: routes, risk segments, checkpoints with tooltips, ETAs and summaries | PASS | Browser run: all routes, selected route coloured by risk, dashed No Travel overlay, checkpoint tooltip (mile, ETA, gust, sustained wind, rain, snow, per-condition and overall level, load-rule line), route cards |
| R6: corridor heatmap, 0-48 h slider, smooth crossfade, synced trucks | PASS | Browser run: 49 bitmaps, crossfading `BitmapLayer`s, trucks at slider time, keyboard (±1 h, Shift ±6 h, Home/End, Space) and 2 h/s playback |

## Performance

| Item | Target | Result |
|---|---|---|
| Plan, server side (`Server-Timing`) | warm < 1.5 s, cold < 3.5 s | **PASS (fake) / NOT VERIFIED (real).** About 30 ms server time with fake providers. Real Mapbox and Open-Meteo latency couldn't be measured |
| Plan, click to cards on screen | (same) | **NOT VERIFIED.** The response arrives about 60 ms after the click, then the first deck.gl draw of real data holds the main thread for about 0.7–1.1 s under SwiftShader. A CPU profile shows about 30 ms of JavaScript; the rest is native GL work (shader linking and first buffer and texture uploads). Needs a run on a real GPU. A shader warm-up removed the linking part but cost about 1 s of blocking time at page load (Lighthouse 66), so it was removed |
| 49 bitmaps ready | < 4 s | **PASS.** About 0.3 s after the heatmap response (the worker renders the current hour first) |
| Slider drag: no long tasks over 50 ms | none | **FAIL (marginal, software GL).** A 10 s drag in the production build showed 0–2 long tasks of 50–51 ms with the heatmap on, and **none** with the heatmap off. Idle 61–63 fps. The cost is CPU-rasterised blending of two full-screen textures. Recheck on a GPU before calling it a pass |
| Route cards and table don't re-render during a drag | none | **PASS.** `ResultsPanel.test.tsx` uses a React Profiler and sees zero commits across 960 hour changes |
| Lighthouse desktop | >= 85 | **PASS.** Performance 99 (FCP 0.5 s, LCP 0.5 s, TBT 100 ms, CLS 0), accessibility 96 (target-size on legend checkboxes, since enlarged), best practices 96 (only the blocked basemap request) |
| Bundle: initial JS | < 250 KB gz | **PASS.** 126 KB |
| Bundle: map chunk | < 450 KB gz | **FAIL.** 512 KB. MapLibre 5 alone is about 265 KB and deck.gl core about 190 KB. Reported as a warning in `make check`; see open decisions |

## Robustness

| Item | Result | Evidence |
|---|---|---|
| Bad geocode | PASS | "No matches" in the combobox; the API returns 404 `GEOCODE_NOT_FOUND` |
| No route (across an ocean) | PASS | 422 `NO_ROUTE`, mapped to "No drivable route" with Retry. Test and fake providers |
| Provider down | PASS | 503 `PROVIDER_UNAVAILABLE`, with retries tested via respx. The UI keeps the form inputs and offers Retry. A heatmap failure shows "Heatmap unavailable · Retry" while the trucks keep working |
| Throttled | PASS | 429 `RATE_LIMITED` with `Retry-After` (test); the UI message includes the wait time |
| Departure 7 days out; low-confidence marked | PASS | `test_far_departure_flags_low_confidence`. Hollow markers on the map, ◌ in the table, a note in the tooltip and a `LOW_CONFIDENCE_FORECAST` note |
| Mobile at 375 px | PASS | Full-screen map, collapsible trip sheet, draggable bottom sheet, slider above the sheet, no horizontal overflow |

## Repo

| Item | Result | Notes |
|---|---|---|
| README complete with live links and Loom | **FAIL** | Not deployed and no Loom recorded. Placeholders are in the README |
| CI green on `main` | **NOT VERIFIED** | No remote yet. `.github/workflows/ci.yml` runs the same steps as `make check`, which passes locally |
| No secrets in history | PASS | `git log -p` scanned for token patterns: nothing |
| `.env.example` complete | PASS | Every variable read in `config/settings` is listed (the platform-provided `RENDER_GIT_COMMIT` and `RAILWAY_GIT_COMMIT_SHA` are mentioned in a comment) |
| Screenshot in `docs/` | PASS | `docs/screenshot.png` (fallback basemap) |

## Open decisions

These need a human call. None of them changes risk logic.

1. **Map chunk budget.** 450 KB gzipped can't be met with the specified MapLibre + deck.gl stack
   (it is 512 KB). Either raise the budget to about 520 KB or change the stack. `make check`
   warns about it and does not fail.
2. **D-06 boundary.** The spec drops a checkpoint *less than* 0.5 mi before the destination;
   the pseudocode in docs/03 §5 also dropped one at exactly 0.5 mi. The code follows the spec,
   and the pseudocode was corrected.
3. **Heatmap encoding.** `round(score*50)` pushed scores at the top of a band (for example 2.999)
   into the next level, which breaks D-15. The code uses `floor(score*50)`, and docs 02 and 03
   were updated.
4. **Missing weather with a known No Travel component.** Per docs/03 §6 the checkpoint becomes
   `UNKNOWN` even if, say, the gust alone is already over 55 mph. That follows the spec literally;
   reporting No Travel in that case may be safer.
5. **MapLibre pinned to 5.x.** deck.gl 9.4's interleaved overlay crashes on every frame with
   MapLibre 6.
