"""route -> sample -> weather -> classify -> attribute -> rank (docs/02 §3)."""

import asyncio
import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from planner.domain.alternatives import (
    RouteCandidate,
    RouteSource,
    candidate_via_points,
    needs_more_routes,
    select_routes,
)
from planner.domain.attribution import owned_intervals, risk_runs, route_stats
from planner.domain.errors import (
    NoRouteError,
    ProviderUnavailableError,
    RouteTooLongError,
)
from planner.domain.eta import capped_durations, cumulative
from planner.domain.geo import segment_lengths_m, simplify_indices, slice_by_distance
from planner.domain.levels import Level, WindMetric
from planner.domain.models import (
    Checkpoint,
    LatLon,
    RiskResult,
    RiskRun,
    RouteGeometry,
    RouteStats,
    WeatherSample,
)
from planner.domain.ranking import Recommendation, RouteScore, recommend
from planner.domain.risk import classify_checkpoint
from planner.domain.sampling import locate, sample_checkpoints
from planner.domain.scenarios import (
    STORMS,
    ScenarioAnchor,
    ScenarioName,
    apply_delta,
    scenario_delta,
)
from planner.domain.units import M_PER_MI, m_to_mi
from planner.domain.weather_lookup import bucket_time, floor_hour, sample_for
from planner.providers.registry import Providers

from .encoding import encode
from .timing import Timings

log = logging.getLogger(__name__)

ROUTE_IDS = ("A", "B", "C")
MAX_ROUTE_MI = 3_000.0  # D-17
LOW_CONFIDENCE_AFTER = timedelta(hours=72)  # D-18
MAX_ROUTE_VERTICES = 2_000
MAX_SEGMENT_VERTICES = 600
VIA_CONCURRENCY = 4


@dataclass(frozen=True, slots=True)
class PlanRequest:
    origin: LatLon
    destination: LatLon
    departure: datetime
    load_lb: int
    interval_mi: int
    scenario: ScenarioName | None = None


@dataclass(frozen=True, slots=True)
class PlanConfig:
    wind_metric: WindMetric = "gust"
    truck_max_speed_mph: float = 65.0
    providers_name: str = "real"


@dataclass(frozen=True, slots=True)
class PlanWarning:
    code: str
    detail: str


@dataclass(frozen=True, slots=True)
class PlannedCheckpoint:
    checkpoint: Checkpoint
    weather: WeatherSample
    risk: RiskResult
    owned_mi: float
    low_confidence: bool


@dataclass(frozen=True, slots=True)
class RiskSegment:
    run: RiskRun
    geometry: str


@dataclass(slots=True)
class PlannedRoute:
    id: str
    label: str
    source: RouteSource
    distance_mi: float
    duration_s: float
    arrival: datetime
    geometry: str
    cum_time_s: list[float]
    checkpoints: list[PlannedCheckpoint]
    stats: RouteStats
    segments: list[RiskSegment]
    rank: int = 0
    recommended: bool = False


@dataclass(slots=True)
class Plan:
    plan_id: str
    generated_at: datetime
    request: PlanRequest
    config: PlanConfig
    routes: list[PlannedRoute]
    recommendation: Recommendation
    warnings: list[PlanWarning] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class _Prepared:
    """A route after the speed cap and simplification, before weather."""

    id: str
    source: RouteSource
    geometry: RouteGeometry
    cum_dist_m: tuple[float, ...]
    cum_dur_s: tuple[float, ...]
    simplified: tuple[LatLon, ...]
    simplified_cum_time_s: tuple[float, ...]
    checkpoints: list[Checkpoint]


async def create_plan(
    req: PlanRequest, providers: Providers, config: PlanConfig, now: datetime, timings: Timings
) -> Plan:
    with timings.measure("routing"):
        candidates = await _fetch_routes(req, providers)
    with timings.measure("compute"):
        prepared = _prepare(candidates, req, config)
    with timings.measure("weather"):
        samples = await _fetch_weather(prepared, req, providers)
    with timings.measure("compute"):
        plan = _assemble(prepared, samples, req, config, now)
    log.info(
        "plan created",
        extra={
            "routes": len(plan.routes),
            "checkpoints": sum(len(r.checkpoints) for r in plan.routes),
            "timings_ms": {k: round(v, 1) for k, v in timings.ms.items()},
        },
    )
    return plan


# --- routing ---


async def _fetch_routes(req: PlanRequest, providers: Providers) -> list[RouteCandidate]:
    routing = providers.routing
    primary = await routing.route(
        req.origin, req.destination, alternatives=True, load_lb=req.load_lb
    )
    primary = [r for r in primary if r.distance_m <= MAX_ROUTE_MI * M_PER_MI]
    if not primary:
        raise RouteTooLongError(f"Routes over {MAX_ROUTE_MI:,.0f} miles are not supported.")
    via_routes: list[RouteGeometry | None] = []
    if needs_more_routes(primary):  # D-13
        sem = asyncio.Semaphore(VIA_CONCURRENCY)

        async def via_route(via: LatLon) -> RouteGeometry | None:
            async with sem:
                try:
                    found = await routing.route(
                        req.origin,
                        req.destination,
                        via=via,
                        alternatives=False,
                        load_lb=req.load_lb,
                    )
                except (NoRouteError, ProviderUnavailableError):
                    return None  # an unreachable via-point is skipped, never fatal
                return next((r for r in found if r.distance_m <= MAX_ROUTE_MI * M_PER_MI), None)

        vias = candidate_via_points(req.origin, req.destination)
        via_routes = list(await asyncio.gather(*(via_route(v) for v in vias)))
    return select_routes(primary, via_routes)


def _prepare(
    candidates: Sequence[RouteCandidate], req: PlanRequest, config: PlanConfig
) -> list[_Prepared]:
    staged = []
    for cand in candidates:
        g = cand.geometry
        cum_dur = cumulative(
            capped_durations(g.seg_dist_m, g.seg_dur_s, config.truck_max_speed_mph)
        )
        staged.append((cum_dur[-1], cand, cum_dur))
    staged.sort(key=lambda s: s[0])  # IDs A, B, C by ascending (truck) duration
    out = []
    for rid, (_, cand, cum_dur) in zip(ROUTE_IDS, staged, strict=False):
        g = cand.geometry
        cum_dist = cumulative(g.seg_dist_m)
        keep = simplify_indices(g.coords, MAX_ROUTE_VERTICES)
        out.append(
            _Prepared(
                id=rid,
                source=cand.source,
                geometry=g,
                cum_dist_m=cum_dist,
                cum_dur_s=cum_dur,
                simplified=tuple(g.coords[i] for i in keep),
                simplified_cum_time_s=tuple(cum_dur[i] for i in keep),
                checkpoints=sample_checkpoints(
                    g.coords, cum_dist, cum_dur, req.departure, req.interval_mi
                ),
            )
        )
    return out


# --- weather ---


def weather_window(departure: datetime, latest_arrival: datetime) -> tuple[datetime, datetime]:
    """docs/03 §6: floor(departure) to ceil(latest arrival) + 1h."""
    return floor_hour(departure), bucket_time(latest_arrival) + timedelta(hours=1)


def scenario_anchor(
    name: ScenarioName, route_a: Sequence[LatLon], cum_dist_m: Sequence[float], start: datetime
) -> ScenarioAnchor:
    fraction = STORMS[name].along_route_fraction
    center, _ = locate(cum_dist_m, cum_dist_m, route_a, cum_dist_m[-1] * fraction)
    return ScenarioAnchor(center=center, start=floor_hour(start))


async def _fetch_weather(
    prepared: Sequence[_Prepared], req: PlanRequest, providers: Providers
) -> list[list[WeatherSample]]:
    points = [cp.position for p in prepared for cp in p.checkpoints]
    latest = max(p.checkpoints[-1].eta for p in prepared)
    start, end = weather_window(req.departure, latest)
    series = await providers.weather.hourly(points, start, end)
    anchor = None
    if req.scenario:
        # Anchor on route A's simplified geometry: the exact line the frontend sends back to
        # /heatmaps, so the checkpoints and the heatmap see the same storm (D-15, D-20).
        a = prepared[0].simplified
        cum = cumulative(segment_lengths_m(a))
        anchor = scenario_anchor(req.scenario, a, cum, req.departure)
    out: list[list[WeatherSample]] = []
    it = iter(series)
    for p in prepared:
        route_samples = []
        for cp in p.checkpoints:
            ws = sample_for(next(it), cp.eta)
            if req.scenario and anchor:
                ws = apply_delta(
                    ws, scenario_delta(req.scenario, anchor, cp.position, ws.forecast_hour)
                )
            route_samples.append(ws)
        out.append(route_samples)
    return out


# --- classify, attribute, rank ---


def _segments(p: _Prepared, runs: Sequence[RiskRun]) -> list[RiskSegment]:
    out = []
    for run in runs:
        part = slice_by_distance(
            p.geometry.coords, p.cum_dist_m, run.from_mi * M_PER_MI, run.to_mi * M_PER_MI
        )
        keep = simplify_indices(part, MAX_SEGMENT_VERTICES)
        out.append(RiskSegment(run, encode([part[i] for i in keep])))
    return out


def _label(summary: str, rid: str) -> str:
    return f"via {summary}" if summary else f"Route {rid}"


def _assemble(
    prepared: Sequence[_Prepared],
    samples: Sequence[Sequence[WeatherSample]],
    req: PlanRequest,
    config: PlanConfig,
    now: datetime,
) -> Plan:
    routes: list[PlannedRoute] = []
    for p, route_samples in zip(prepared, samples, strict=True):
        risks = [classify_checkpoint(ws, req.load_lb, config.wind_metric) for ws in route_samples]
        total_mi = m_to_mi(p.cum_dist_m[-1])
        intervals = owned_intervals([cp.mile for cp in p.checkpoints], total_mi)
        levels = [r.overall for r in risks]
        planned_cps = [
            PlannedCheckpoint(
                checkpoint=cp,
                weather=ws,
                risk=risk,
                owned_mi=right - left,
                low_confidence=cp.eta - now > LOW_CONFIDENCE_AFTER,  # D-18
            )
            for cp, ws, risk, (left, right) in zip(
                p.checkpoints, route_samples, risks, intervals, strict=True
            )
        ]
        duration = p.cum_dur_s[-1]
        routes.append(
            PlannedRoute(
                id=p.id,
                label=_label(p.geometry.summary, p.id),
                source=p.source,
                distance_mi=total_mi,
                duration_s=duration,
                arrival=req.departure.astimezone(UTC) + timedelta(seconds=duration),
                geometry=encode(p.simplified),
                cum_time_s=[round(t, 1) for t in p.simplified_cum_time_s],
                checkpoints=planned_cps,
                stats=route_stats(intervals, levels),
                segments=_segments(p, risk_runs(intervals, levels)),
            )
        )
    recommendation, ranked = recommend([RouteScore(r.id, r.duration_s, r.stats) for r in routes])
    rank_of = {score.route_id: i + 1 for i, score in enumerate(ranked)}
    for r in routes:
        r.rank = rank_of[r.id]
        r.recommended = r.id == recommendation.route_id
    return Plan(
        plan_id=f"pln_{uuid.uuid4().hex[:20]}",
        generated_at=now,
        request=req,
        config=config,
        routes=routes,
        recommendation=recommendation,
        warnings=_warnings(routes, req),
    )


def _warnings(routes: Sequence[PlannedRoute], req: PlanRequest) -> list[PlanWarning]:
    out = []
    if len(routes) < len(ROUTE_IDS):  # D-13
        noun = "route exists" if len(routes) == 1 else "routes exist"
        out.append(
            PlanWarning(
                "ONLY_N_DISTINCT_ROUTES", f"Only {len(routes)} distinct {noun} for this trip."
            )
        )
    gaps = sum(1 for r in routes for cp in r.checkpoints if cp.risk.overall is Level.UNKNOWN)
    if gaps:
        out.append(
            PlanWarning(
                "WEATHER_GAPS",
                f"No forecast for {gaps} checkpoint{'s' if gaps > 1 else ''}. "
                "Those miles are left out of the risk totals, not counted as safe.",
            )
        )
    if any(cp.low_confidence for r in routes for cp in r.checkpoints):
        out.append(
            PlanWarning(
                "LOW_CONFIDENCE_FORECAST",
                "Some checkpoints are more than 72 hours out, where forecasts are less reliable.",
            )
        )
    if req.scenario:
        out.append(
            PlanWarning(
                "SIMULATED_WEATHER",
                f"Simulated weather ({req.scenario.replace('_', ' ')}) is layered on the forecast.",
            )
        )
    return out
