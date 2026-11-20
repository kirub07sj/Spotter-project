# AGENTS.md

Rules for every AI coding agent (Claude Code, Cursor, Codex, Copilot) and every human working in this repo.

**Project:** Weather-Aware Truck Routing (Spotter full stack assessment)
**Stack:** Django 5 + DRF (backend), React + TypeScript + Vite + Tailwind (frontend), MapLibre GL + deck.gl (map)
**Grading weights:** 40% routing, weather, risk and recommendation logic. 40% UI, map and heatmap smoothness and performance. 15% code quality. 5% docs and walkthrough.

---

## 1. Read before you write code

Read these in order before starting any task. They are short on purpose.

1. `docs/01-SPEC.md`: requirements, the decisions log (D-01 to D-20), and the traceability table
2. `docs/02-ARCHITECTURE.md`: modules, API contract, data flow, config
3. `docs/03-ALGORITHMS.md`: every calculation with pseudocode and edge cases
4. `docs/04-UI-DESIGN.md`: layout, map layers, heatmap rendering, performance budget
5. `docs/05-ENGINEERING-PRACTICES.md`: code style, testing, CI, review checklist
6. `docs/06-DELIVERY.md`: deploy, README, Loom script, final QA

Task-specific skills live in `.claude/skills/`. Load the matching one before you touch that area:

| Area | Skill |
|---|---|
| Risk classification, sampling, mile attribution, ranking | `.claude/skills/risk-engine/SKILL.md` |
| Mapbox, Open-Meteo, caching, retries, unit conversion | `.claude/skills/provider-integration/SKILL.md` |
| Map layers, heatmap worker, slider, rendering performance | `.claude/skills/map-performance/SKILL.md` |

---

## 2. Golden rules

1. **The spec is law.** Thresholds, load rules and ranking order come from `docs/01-SPEC.md`. Never change a number unless you update the spec, the decisions log and the tests in the same change.
2. **Never resolve an ambiguity silently.** If the spec and decisions log don't cover a case, stop. Add a proposed decision (`D-xx`, status `PROPOSED`) to the decisions log and ask the human.
3. **Correctness before features.** Build nothing outside the spec until every requirement in the traceability table passes. Optional ideas go in the "Stretch" list in the spec.
4. **The domain layer is pure.** Code in `backend/planner/domain/` must not import Django, httpx, or anything that does I/O, and must not call `datetime.now()`. Pass time in as an argument. Domain code must be testable with plain pytest in milliseconds.
5. **Units are converted exactly once.** Providers return metric. Adapters convert to domain units through `domain/units.py` and nowhere else. Domain units are: miles, seconds, mph, inches per hour, pounds, UTC-aware `datetime`.
6. **UTC everywhere on the backend.** Aware datetimes only. The API sends ISO 8601 with offset. Only the frontend formats to local time.
7. **No network call on slider movement.** Dragging the forecast slider must only change layer props on data that's already loaded. This is a hard performance rule.
8. **Every rule ships with tests.** Any change to classification, attribution or ranking needs boundary tests. Every threshold edge (24.99, 25.0, 34.99, 35.0 and so on) must be tested.
9. **The API contract is generated.** The backend schema comes from drf-spectacular. Frontend types come from `openapi-typescript`. Never hand-edit `frontend/src/api/schema.d.ts`.
10. **No secrets in the repo.** Keys are read from the environment. Update `.env.example` whenever you add a variable.
11. **Keep it small.** No new dependency without a one-line reason in the PR or commit body. Prefer the standard library, numpy and shapely on the backend, and the existing stack on the frontend.
12. **Be honest in the UI.** If fewer than 3 distinct routes exist, or the weather is simulated, or a forecast is past 72 hours, say so on screen.

---

## 3. Repository map

```
.
├── AGENTS.md                  # this file
├── CLAUDE.md                  # Claude Code entry point (imports this file)
├── README.md                  # setup, decisions summary, links (see docs/06)
├── docs/                      # spec, architecture, algorithms, UI, practices, delivery
├── .claude/skills/            # task skills for agents
├── backend/
│   ├── config/                # settings (base, dev, prod), urls, asgi
│   ├── planner/
│   │   ├── domain/            # PURE: models, units, geo, sampling, risk, attribution, ranking, heatmap
│   │   ├── providers/         # Mapbox routing + geocoding, Open-Meteo weather, fakes
│   │   ├── services/          # orchestration: plan_service, heatmap_service
│   │   ├── api/               # DRF views, serializers, urls, error handlers
│   │   └── tests/             # unit (domain), contract (api), adapter (providers + fixtures)
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/               # fetch client, generated schema types, query hooks
│   │   ├── features/
│   │   │   ├── plan-form/     # origin, destination, departure, load, interval
│   │   │   ├── routes/        # route cards, recommendation banner, checkpoint table
│   │   │   ├── map/           # MapView, deck layers, legend, truck marker
│   │   │   └── heatmap/       # worker, colormap, slider, playback
│   │   ├── store/             # zustand UI state
│   │   ├── lib/               # risk levels, colors, formatting, polyline
│   │   └── main.tsx
│   └── package.json
└── .github/workflows/ci.yml
```

---

## 4. Commands

```bash
# backend
cd backend
uv sync                                   # install
uv run python manage.py runserver         # dev server on :8000
uv run pytest -q                          # tests
uv run ruff check . && uv run ruff format --check .
uv run mypy planner                       # strict on domain/
uv run python manage.py spectacular --file ../frontend/openapi.yaml

# frontend
cd frontend
pnpm install
pnpm dev                                  # Vite on :5173, proxies /api to :8000
pnpm gen:api                              # openapi.yaml -> src/api/schema.d.ts
pnpm test                                 # vitest
pnpm lint && pnpm typecheck
pnpm build
```

Run the full check before you call any task done:

```bash
make check   # runs backend lint, types, tests, then frontend lint, typecheck, test, build
```

---

## 5. Build order (milestones)

Work strictly in this order. Don't start a milestone until the previous one is green.

| # | Milestone | Done when |
|---|---|---|
| M0 | Scaffold | Both apps run, CI green, `/api/v1/health` returns 200, `.env.example` present |
| M1 | Domain engine | `units`, `geo`, `sampling`, `risk`, `attribution`, `ranking` implemented with 100% branch coverage on `risk` and `ranking` |
| M2 | Providers | Mapbox routing (with via-point fallback), geocoding, Open-Meteo batched fetch, all tested against recorded fixtures, fakes available |
| M3 | Plan API | `POST /api/v1/plans` returns the full contract, golden-scenario test passes end to end with fake providers |
| M4 | Map and routes UI | Form, 3 routes on the map, risk-colored selected route, checkpoints with tooltips, route cards, recommendation banner |
| M5 | Heatmap | `POST /api/v1/heatmaps`, worker-rendered rasters, slider and playback at 60 fps, truck position marker |
| M6 | Polish | Loading, empty and error states, responsive layout, accessibility pass, simulated-weather scenario mode |
| M7 | Ship | Deployed backend and frontend, README complete, Loom recorded, final QA checklist in `docs/06` ticked |

---

## 6. Definition of done (every task)

- [ ] Behaviour matches the spec and decisions log
- [ ] Tests added or updated, and they fail without your change
- [ ] `make check` passes locally
- [ ] No new `any` in TypeScript, no `# type: ignore` without a reason comment
- [ ] No `print`, `console.log` or commented-out code left behind
- [ ] API change? Schema regenerated and frontend types updated in the same commit
- [ ] Docs updated if behaviour, config or a decision changed
- [ ] Commit message follows Conventional Commits

---

## 7. When to stop and ask

Stop and ask the human instead of guessing when:

- A provider returns data shaped differently from the recorded fixtures
- A decision in the spec seems wrong (explain why, don't just change it)
- A fix needs a new paid service, a new provider, or a new major dependency
- Performance budgets can't be met with the planned approach
- You'd need to change more than about 300 lines to finish one task

---

## 8. Style summary

**Python:** 3.12, ruff (lint + format), mypy strict on `planner/domain`. Frozen dataclasses with `slots=True` for domain models. Type hints everywhere. Functions under about 40 lines. Name things by what they mean (`checkpoint_eta_utc`, not `t2`).

**TypeScript:** strict mode, no `any`, no default exports except route pages. Components are function components. Server state goes in TanStack Query, UI state in zustand. Keep heavy compute out of React render (use workers and `useMemo`).

**Commits:** Conventional Commits (`feat(risk): apply load rules to wind level`). Keep them small and focused, and keep the build green after each one.

**Comments:** explain *why*, not *what*. Reference decision IDs where they apply, for example `# D-08: use the hour bucket that ends at or after the ETA`.
