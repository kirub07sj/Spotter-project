# 06. Delivery: Deploy, README, Loom, Final QA

## 1. Deploy

**Backend (Render, Railway or Fly.io)**
1. Create a web service from `backend/`.
2. Build: `pip install uv && uv sync --frozen && uv run python manage.py collectstatic --noinput`
3. Start: `uv run gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:$PORT`
4. Env vars: everything in `.env.example`. Set `DJANGO_DEBUG=false`, `DJANGO_ALLOWED_HOSTS=<backend host>` and `CORS_ALLOWED_ORIGINS=<frontend url>`.
5. Health check path: `/api/v1/health`.
6. Use an instance that **doesn't sleep** during the review window. A cold start of 30 seconds or more on the reviewer's first click undermines the performance grade.

**Frontend (Vercel or Netlify)**
1. Root `frontend/`, build `pnpm build`, output `dist`.
2. Env: `VITE_API_BASE_URL=https://<backend>/api/v1`, `VITE_MAP_STYLE_URL=<style json>`.
3. Add an SPA fallback rewrite to `index.html`.

**Mapbox token:** restrict it to the backend (it's only used server side). Set a usage alert on the account.

**After deploying:** open the hosted app in a private window, plan the demo trip, check the `Server-Timing` header in devtools, and confirm `/health` shows the expected git SHA.

## 2. README template

```markdown
# Weather-Aware Truck Routing

Live app: <url> · API health: <url>/api/v1/health · Walkthrough: <loom url>

Compare 3 truck routes by forecast weather at the time the truck reaches each checkpoint,
then pick the safest one using wind, rain and snow thresholds and load weight rules.

![screenshot](docs/screenshot.png)

## How it works (60 seconds)
1. Mapbox gives up to 3 routes (extra distinct routes generated with via-points if needed).
2. Checkpoints every 10/25/50 miles get an ETA from route durations (truck speed capped at 65 mph).
3. Open-Meteo hourly forecasts are looked up at each checkpoint's ETA.
4. Each checkpoint is classified Low to No Travel. Load rules adjust the wind level.
5. Each checkpoint owns the road halfway to its neighbours. Routes are ranked by
   No Travel miles, Severe miles, High miles, average risk, then travel time.

## Key decisions
Short table of D-01, D-04, D-08, D-09, D-11, D-13, D-14 with one line each, and a link to docs/01-SPEC.md.

## Run locally
backend and frontend commands, .env setup

## Tests
how to run, what's covered (boundary, property, golden scenarios)

## Architecture
the diagram from docs/02, the folder map

## Performance notes
heatmap bitmap pipeline, no network on slider, Server-Timing

## Limitations and next steps
HOS not modelled, car-based routing, forecast skill beyond 72h, S-01 to S-04
```

## 3. Loom script (target 8 minutes)

The time split mirrors the grading weights.

| Time | Section | What to show |
|---|---|---|
| 0:00-0:30 | Intro | Who you are, what the app does in one sentence, the stack |
| 0:30-2:30 | Live demo (real weather) | Plan a mountain or winter corridor, for example Denver to Salt Lake City, load 42,000 lb, 25 mi interval. Walk the banner, route cards, risk bars, checkpoint tooltip. Switch to the 10 mi interval. Play the slider and point at the truck markers moving with the weather |
| 2:30-3:30 | Simulated scenario | Turn on `winter_storm`. Show the recommendation change and the reasons text. Change the load from 35,000 to 45,000 lb and show the load rule flipping a checkpoint to Severe or No Travel |
| 3:30-5:00 | Logic (40%) | `levels.py` thresholds and D-01 boundaries, `classify_wind` load rules, D-08 bucket choice, D-09 mile attribution, the ranking key and why No Travel comes first. Run the boundary tests and golden scenario tests on screen |
| 5:00-6:30 | Performance (40%) | Devtools: `Server-Timing` on `/plans`, the Performance panel while dragging the slider (no long tasks), the worker posting bitmaps. Explain why not `HeatmapLayer` |
| 6:30-7:30 | Code quality (15%) | Folder structure, pure domain, providers behind Protocols, generated API types, CI checks |
| 7:30-8:00 | Wrap-up | Trade-offs (strict ranking order, car-based durations, no HOS) and what you'd do next |

Tips: record at 1080p, zoom the browser to 110%, close other tabs, and pre-warm the backend and cache by planning the demo trip once before recording.

## 4. Final QA checklist

**Requirements**
- [ ] R1: 3 routes for a long trip. The warning shows when fewer than 3 exist
- [ ] R2: interval switch 10/25/50 changes the checkpoint count. ETAs increase along the route
- [ ] R3: boundary values from the test table give the expected levels through the API (use the scenario or a fake)
- [ ] R4: banner reasons match the card stats. NO_SAFE_ROUTE case renders
- [ ] R5: all routes, risk segments, checkpoints with tooltips, ETAs and summaries visible on the map and cards
- [ ] R6: heatmap visible along the corridor, slider 0-48h, crossfade smooth, truck markers synced

**Performance**
- [ ] Warm plan under 1.5 s, cold under 3.5 s (Server-Timing)
- [ ] 49 bitmaps ready under 4 s
- [ ] Slider drag shows no long tasks over 50 ms in the Performance panel
- [ ] Lighthouse desktop >= 85

**Robustness**
- [ ] Bad geocode, no route (for example across an ocean), provider down (block it in devtools), throttled requests: each shows a clear message and retry
- [ ] Departure 7 days out works, and low-confidence checkpoints are marked
- [ ] Mobile layout usable at 375 px wide

**Repo**
- [ ] README complete with live links and the Loom
- [ ] CI green on `main`
- [ ] No secrets in history (`git log -p | grep -i token` returns nothing sensitive)
- [ ] `.env.example` complete
- [ ] Screenshot in `docs/`
