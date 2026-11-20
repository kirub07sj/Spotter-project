# Final QA report (docs/06 §4)

## Follow-up audit and fixes · 2026-11-20

This section supersedes the original results below where they differ. The project is
**not fully signed off**: Mapbox needs a token and delivery
work remains. Passing unit tests alone is not a full acceptance result.

### Specification coverage

| Decisions | Current evidence |
|---|---|
| D-01–D-05: thresholds, component maximum/ties, load rules, gusts, rain + showers | Boundary/property/adapter tests pass. Risk and ranking retain 100% branch coverage |
| D-06–D-10: checkpoint spacing, capped ETAs, ending hourly buckets, midpoint ownership, weighted risk | Domain tests pass, including exact 0.5 mi, zero-length segments, timezone changes and missing weather |
| D-11–D-12: ranking and No Travel status | Golden scenarios pass. New tests prove even 0.000001 No Travel miles produces `NO_SAFE_ROUTE`; status no longer uses rounded miles |
| D-13: distinct alternatives and warnings | Fake-provider contract tests pass, including filtering overlong primary/via alternatives. Live Mapbox verification remains blocked |
| D-14–D-16: heatmap timeline, scoring and corridor | Frames cover exact departure +0 to +48 h. New tests cover minutes 1, 30 and 59 and compare scenario grid scores with checkpoint classification for a half-hour departure |
| D-17: validation | Tests cover load/time/interval bounds, identical locations and route lengths. All returned alternatives respect the 3,000 mi limit. An undocumented 0.1 mi minimum separation was removed; nearby distinct locations are valid |
| D-18–D-20: confidence, local times, simulation | Tests cover >72 h flags, local formatting and scenarios. Low-confidence markers now have dashed SVG rings; simulated/demo data remains labelled |

### Additional rule checks

The latest delivery `make check` passed locally with 301 backend tests, 59 frontend tests and four bundle-gate
tests, plus lint, types, import rules, schema drift, build and size checks. The domain
retains 100% branch coverage.

- Native async API handlers now await services on the ASGI loop. DRF synchronous
  authentication/throttle checks run in a thread; contract tests still verify errors,
  malformed JSON, method rejection, OPTIONS and throttling. Uvicorn health/geocoding smoke
  checks also pass.
- Retry tests cover all 5xx codes, long numeric `Retry-After` and HTTP-date values.
  Each network attempt has a total timeout in addition to httpx phase timeouts.
- Route-layer data arrays remain stable across forecast updates. Regression tests check
  buffer references, and the existing React Profiler test checks that route cards/table
  do not re-render during slider movement.
- Reduced-motion users retain manual slider controls while playback is disabled.
- Worker replacement closes pending bitmaps, cancels queued completion updates and ignores
  stale completion messages; regression tests cover these cases.
- Domain import rules, strict types, lint/formatting and generated API schema/types are
  checked by `make check`. A tracked-history scan found no matches for common Mapbox,
  OpenAI or GitHub token patterns; this is a pattern scan, not proof against every secret.

### Browser and live-provider results

Production build, Chromium with hardware OpenGL, AMD Radeon Graphics (radeonsi renoir ACO),
1440 × 900 viewport: the final-build slider drag averaged **59.9 fps**, with **zero tasks
over 50 ms** and **zero API requests**. The heatmap worker completed in **105 ms**. Keyboard navigation,
reduced-motion controls and layout at 1440 × 900, 1200 × 700 and 390 × 844 passed.
Software rendering remains substantially slower and is not reported as a performance pass.

The live Open-Meteo adapter successfully fetched a batch of two locations and three hourly
buckets, parsing metric conversion. No Mapbox token is configured, so live routing, real
route latency and a complete real-provider trip remain **NOT VERIFIED**. The recorded
Mapbox fixtures remain synthetic. Two Open-Meteo fixtures were subsequently replaced
with real responses and capture provenance on 2026-11-20; nonzero conversion/null stress
cases remain synthetic. The original Lighthouse result below was not rerun.

Repeat browser checks with the demo backend running and `pnpm build && pnpm preview`:

```bash
cd backend
uv run --with playwright python scripts/check_browser.py --url http://localhost:4173 \
  --browser /path/to/chrome --angle gl
```

Playwright is optional QA tooling; it is not an application dependency. The script reports
the renderer and long tasks so a software-rendered run is distinguishable from hardware.

### Remaining acceptance blockers

The WebGL-only deck.gl build reduces map JavaScript from 511.7 KB to about **474 KB
gzipped**. The human approved the **475 KB** budget in D-21 on 2026-11-20. This gate now
passes; both bundle budgets fail the build when exceeded.

1. Provide a local Mapbox token, run real routing/geocoding and record real fixtures.
   Recheck performance with the real providers, including seven-day departures.
2. Deploy the frontend/backend, add the live links and record the Loom.
   These deliverables remain incomplete. Stretch features remain optional and unimplemented.

Repository publication and remote checks are tracked at
[RasAbrish/spotter Actions](https://github.com/RasAbrish/spotter/actions/workflows/ci.yml).
Require a successful run for the repository's current head before delivery.

### Delivery execution · 2026-11-20

- Created and pushed the private `RasAbrish/spotter` repository. Repository-local Git
  configuration uses the user's authenticated SSH key; no credentials are committed.
- GitHub Actions is enabled and allows all actions. Push and manual runs both returned
  `startup_failure` before creating any jobs or logs. The manual
  [CI run](https://github.com/RasAbrish/spotter/actions/runs/44730189703) uses the actual
  `.github/workflows/ci.yml` workflow. The API supplies no further error message; the
  owner must inspect the run page before this can be marked green.
- The documented production command, Gunicorn with two Uvicorn workers and production
  Django settings, passed local health, geocoding, winter-storm planning and 49-frame
  heatmap smoke checks with offline providers and a generated environment-only secret.
- A Docker image build was attempted but stopped during a very slow upstream registry
  download. The complete container build is **not verified**; the native Render command
  was verified separately. No cloud services have been provisioned or charged.
- Render/Vercel connections and approval for the existing paid Render backend/Redis
  blueprint remain pending. The local Mapbox token is still absent.

## Original delivery run

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

1. **Map chunk budget — resolved by D-21 in the follow-up above.** The original run
   measured 512 KB against 450 KB. The current WebGL-only build is about 474 KB against
   the human-approved 475 KB budget; the gate now fails on an excess.
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
