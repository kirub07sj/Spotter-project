# 05. Engineering Practices

Code quality is 15% of the grade, but it also decides how fast you can fix the logic (40%) and the UI (40%). Keep it boring and consistent.

## 1. Tooling

| Concern | Backend | Frontend |
|---|---|---|
| Runtime | Python 3.12, Django 5.x, DRF, ASGI (uvicorn) | Node 20+, React 18/19, Vite, TypeScript strict |
| Packages | `uv` | `pnpm` |
| Lint + format | `ruff check`, `ruff format` | ESLint (typescript-eslint, react-hooks), Prettier |
| Types | `mypy --strict` on `planner/domain`, normal on the rest | `tsc --noEmit` |
| Tests | pytest, pytest-asyncio, Hypothesis, respx (HTTP mocks), pytest-socket (blocks real network) | Vitest, Testing Library, optional Playwright smoke test |
| Schema | drf-spectacular | openapi-typescript |
| Architecture rule | import-linter (domain imports nothing from api, services or providers) | eslint `no-restricted-imports` (features don't import each other's internals) |
| Hooks | pre-commit: ruff, mypy (domain), prettier, eslint | |

Key libraries: `httpx`, `numpy`, `shapely`, `polyline` (backend). `maplibre-gl`, `react-map-gl`, `@deck.gl/core`, `@deck.gl/layers`, `@deck.gl/mapbox`, `@tanstack/react-query`, `zustand`, `zod`, `react-hook-form`, `@mapbox/polyline` (frontend).

## 2. Backend conventions

- **Domain models** are `@dataclass(frozen=True, slots=True)`. No ORM models are needed.
- **Pure functions** take every input as an argument (including `now` and `settings` values). No module-level state apart from constants.
- **Thresholds live in one place:** `domain/levels.py`. Tests import from there, so a change shows up everywhere.
- **Providers** implement Protocols from `providers/base.py`. Services depend on the Protocol, never on the concrete class. Wire them up in one `providers/registry.py` driven by settings (`real` or `fake`).
- **Errors:** domain raises typed exceptions (`NoRouteError`, `ProviderUnavailableError`, `ValidationError`). `api/errors.py` maps them to problem+json. Views never catch `Exception` broadly.
- **Serializers** validate input (D-17) and shape output. No business logic in serializers or views.
- **Logging:** `structlog` or the stdlib with a JSON formatter. Log provider latency and counts, never tokens.
- **Settings:** `config/settings/{base,dev,prod}.py`. Every setting read from the environment has a default in `.env.example`.

## 3. Frontend conventions

- **Feature folders** own their components, hooks and tests. Shared code only goes in `lib/` once two features use it.
- **API layer:** a typed `apiFetch<T>()` wrapper that parses problem+json into an `ApiError` with a `code`. Query hooks live in `api/hooks.ts`.
- **No business logic duplication.** The frontend never re-classifies risk. It renders what the API returns. The one exception is the truck position interpolation, which is presentation only.
- **Components** stay under about 150 lines. Pull out hooks for logic, keep JSX declarative.
- **Styling:** Tailwind utility classes. Design tokens (risk colors, route colors, spacing) live in `tailwind.config.ts` and `lib/risk.ts`. No inline hex values in components.
- **Workers:** Vite `new Worker(new URL('./heatmap.worker.ts', import.meta.url), { type: 'module' })`. Messages are typed with a discriminated union.

## 4. Testing strategy

| Layer | What | Target |
|---|---|---|
| Domain unit | risk boundaries, properties, sampling, attribution, ranking, heatmap scoring | 100% branch coverage on `risk.py` and `ranking.py`, >= 90% on domain overall |
| Golden scenarios | 6 hand-written end-to-end cases through `plan_service` with fake providers (03-ALGORITHMS section 9) | all pass, the expected output is written by hand and never generated |
| Provider adapters | Parse the recorded Mapbox and Open-Meteo fixtures, check unit conversion, retries on 429/5xx, null handling | respx, no real network |
| API contract | Request validation, response shape against the schema, error codes | DRF test client |
| Frontend unit | `lib/risk.ts`, formatters, polyline decode, truck interpolation, worker bilinear + LUT | Vitest |
| Frontend component | PlanForm validation, RouteCard rendering, Banner variants, slider keyboard | Testing Library |
| Smoke (optional) | Playwright: plan a trip with the fake backend, see 3 cards, drag the slider | 1 test |

**Rules**
- Write the boundary tests first for any rule in `risk.py`.
- A bug fix starts with a failing test that reproduces it.
- Tests can't hit the network. `pytest-socket` enforces this.
- Fixtures are real recorded responses with tokens stripped, stored under `tests/fixtures/{provider}/{case}.json`.

## 5. CI (`.github/workflows/ci.yml`)

Two jobs that run in parallel on every push and PR:
- **backend:** `uv sync`, ruff check, ruff format --check, mypy, lint-imports, pytest with coverage (fail under 90% on domain)
- **frontend:** `pnpm install --frozen-lockfile`, lint, typecheck, test, build, then a bundle size check (fails if the initial chunk is over 250 KB gzipped)

Also add a job that runs `manage.py spectacular` and fails if `frontend/openapi.yaml` is out of date.

## 6. Git workflow

- `main` is always deployable. Work on short-lived branches `feat/…`, `fix/…`, `chore/…`.
- Conventional Commits: `feat(ranking): add No Travel miles as first key (D-11)`.
- One logical change per commit. Reference decision IDs where relevant.
- Squash-merge PRs. A reviewer can read the history as a story of the build. Reviewers at Spotter will look at it.

## 7. Code review checklist

**Correctness**
- [ ] Does it follow the decisions log? Are the D-xx IDs referenced in comments where the reasoning isn't obvious?
- [ ] Are units converted only in `units.py`?
- [ ] Are datetimes UTC-aware with no naive datetimes?
- [ ] Are edge cases from 03-ALGORITHMS section 13 handled?

**Performance**
- [ ] Is there any network or heavy compute on slider change? (Must be none.)
- [ ] Are provider calls batched and parallel where possible?
- [ ] Are big arrays kept out of React state that changes often?

**Quality**
- [ ] Are names clear? Are functions small? Is there dead code?
- [ ] Do tests cover the change and fail without it?
- [ ] Do types pass with no `any` or `type: ignore` without a reason?
- [ ] Were the docs updated if behaviour or config changed?

## 8. Things to avoid

- Classifying risk in the frontend "for speed". There must be one source of truth.
- Hard-coding thresholds in tests. Import them from `levels.py`.
- `useEffect` chains that fetch on every state change. Use query keys instead.
- deck.gl `HeatmapLayer` for this data. It aggregates point *density*, but our data is a field of *values*. Use the bitmap pipeline.
- Re-encoding or re-decoding polylines on every render.
- Swallowing provider errors and returning "Low" risk. Unknown weather is never safe weather.
