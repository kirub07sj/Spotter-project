"""Hand-written golden scenarios shared by the domain-level and end-to-end tests.

Weather values below are chosen to sit clearly inside a band: wind (gust) 10 = Low,
40 = High (Severe with load > 40,000 lb), 50 = Severe (No Travel with load > 30,000 lb),
60 = No Travel; rain 0.30 = High; snow 0.7 = Moderate, 2.5 = Severe, 3.5 = No Travel."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from planner.domain.attribution import owned_intervals, route_stats
from planner.domain.models import WeatherSample
from planner.domain.ranking import Recommendation, RouteScore, recommend
from planner.domain.risk import classify_checkpoint

ROUTE_MI = 100.0
INTERVAL_MI = 25
CHECKPOINT_MILES = [0.0, 25.0, 50.0, 75.0, 100.0]
DEPARTURE = datetime(2026, 11, 20, 13, 0, tzinfo=UTC)


@dataclass(frozen=True)
class W:
    gust: float = 10.0
    rain: float = 0.0
    snow: float = 0.0


CALM = W()


@dataclass(frozen=True)
class GoldenRoute:
    minutes: int
    weather: tuple[W, W, W, W, W]  # one per checkpoint at miles 0, 25, 50, 75, 100


@dataclass(frozen=True)
class GoldenScenario:
    routes: dict[str, GoldenRoute]
    load_lb: int
    expected_winner: str
    expected_status: str
    expected_order: list[str]
    expected_reasons: tuple[str, ...]
    note: str = field(default="")


def at(**overrides: W) -> tuple[W, W, W, W, W]:
    """at(cp2=W(gust=50)) -> weather tuple with checkpoint 2 overridden, the rest calm."""
    cps = [CALM] * 5
    for key, value in overrides.items():
        cps[int(key.removeprefix("cp"))] = value
    return (cps[0], cps[1], cps[2], cps[3], cps[4])


GOLDEN_SCENARIOS: dict[str, GoldenScenario] = {
    "severe_decides": GoldenScenario(
        note="B has the most High miles and is slower, but it is the only one with no Severe.",
        routes={
            "A": GoldenRoute(100, at(cp2=W(gust=50))),  # Severe 25
            "B": GoldenRoute(110, at(cp1=W(gust=40), cp3=W(gust=40))),  # High 50
            "C": GoldenRoute(120, at(cp0=W(snow=2.5))),  # Severe 12.5
        },
        load_lb=20_000,
        expected_winner="B",
        expected_status="OK",
        expected_order=["B", "C", "A"],
        expected_reasons=(
            "Chosen over C: 12.5 fewer Severe miles",
            "Chosen over A: 25.0 fewer Severe miles",
        ),
    ),
    "high_decides": GoldenScenario(
        routes={
            "A": GoldenRoute(100, at(cp1=W(gust=40), cp2=W(gust=50))),  # Sev 25, High 25
            "B": GoldenRoute(130, at(cp2=W(snow=2.5))),  # Sev 25
            "C": GoldenRoute(110, at(cp1=W(rain=0.3), cp2=W(gust=50), cp3=W(gust=40))),
        },
        load_lb=20_000,
        expected_winner="B",
        expected_status="OK",
        expected_order=["B", "A", "C"],
        expected_reasons=(
            "Chosen over A: same Severe miles, 25.0 fewer High miles",
            "Chosen over C: same Severe miles, 50.0 fewer High miles",
        ),
    ),
    "avg_risk_decides": GoldenScenario(
        note="All routes have 12.5 High miles (destination) and no Severe.",
        routes={
            "A": GoldenRoute(100, at(cp1=W(snow=0.7), cp2=W(snow=0.7), cp4=W(rain=0.3))),
            "B": GoldenRoute(140, at(cp2=W(snow=0.7), cp4=W(rain=0.3))),
            "C": GoldenRoute(
                90, at(cp1=W(snow=0.7), cp2=W(snow=0.7), cp3=W(snow=0.7), cp4=W(rain=0.3))
            ),
        },
        load_lb=20_000,
        expected_winner="B",
        expected_status="OK",
        expected_order=["B", "A", "C"],
        expected_reasons=(
            "Chosen over A: same Severe and High miles, lower average risk (0.50 vs 0.75)",
            "Chosen over C: same Severe and High miles, lower average risk (0.50 vs 1.00)",
        ),
    ),
    "duration_decides": GoldenScenario(
        routes={
            "A": GoldenRoute(100, at(cp2=W(snow=0.7))),
            "B": GoldenRoute(118, at(cp2=W(snow=0.7))),
            "C": GoldenRoute(125, at(cp2=W(snow=0.7))),
        },
        load_lb=20_000,
        expected_winner="A",
        expected_status="OK",
        expected_order=["A", "B", "C"],
        expected_reasons=(
            "Chosen over B: same risk profile, 18 min faster",
            "Chosen over C: same risk profile, 25 min faster",
        ),
    ),
    "no_safe_route": GoldenScenario(
        routes={
            "A": GoldenRoute(100, at(cp2=W(gust=60))),  # NT 25
            "B": GoldenRoute(110, at(cp1=W(gust=60), cp2=W(gust=60))),  # NT 50
            "C": GoldenRoute(120, at(cp2=W(snow=3.5), cp3=W(snow=2.5))),  # NT 25, Sev 25
        },
        load_lb=20_000,
        expected_winner="A",
        expected_status="NO_SAFE_ROUTE",
        expected_order=["A", "C", "B"],
        expected_reasons=(
            "Chosen over C: same No Travel miles, 25.0 fewer Severe miles",
            "Chosen over B: 25.0 fewer No Travel miles",
        ),
    ),
}

_LOAD_FLIP_ROUTES = {
    "A": GoldenRoute(100, at(cp2=W(gust=40))),  # High at 35k, Severe (load rule) at 45k
    "B": GoldenRoute(110, at(cp1=W(rain=0.3), cp3=W(rain=0.3))),  # High 50 at any load
    "C": GoldenRoute(105, at(cp1=W(snow=2.5), cp3=W(rain=0.3))),  # Severe 25, High 25
}
GOLDEN_SCENARIOS["load_flip_35k"] = GoldenScenario(
    routes=_LOAD_FLIP_ROUTES,
    load_lb=35_000,
    expected_winner="A",
    expected_status="OK",
    expected_order=["A", "B", "C"],
    expected_reasons=(
        "Chosen over B: same Severe miles, 25.0 fewer High miles",
        "Chosen over C: 25.0 fewer Severe miles",
    ),
)
GOLDEN_SCENARIOS["load_flip_45k"] = GoldenScenario(
    routes=_LOAD_FLIP_ROUTES,
    load_lb=45_000,
    expected_winner="B",
    expected_status="OK",
    expected_order=["B", "A", "C"],
    expected_reasons=(
        "Chosen over A: 25.0 fewer Severe miles",
        "Chosen over C: 25.0 fewer Severe miles",
    ),
)


def weather_sample(w: W, hour: datetime = DEPARTURE) -> WeatherSample:
    return WeatherSample(
        wind_mph=w.gust * 0.7,
        gust_mph=w.gust,
        rain_in_hr=w.rain,
        snow_in_hr=w.snow,
        forecast_hour=hour,
    )


@dataclass(frozen=True)
class DomainResult:
    recommendation: Recommendation
    order: list[str]
    load_adjusted: dict[str, list[bool]]


def run_domain_pipeline(scenario: GoldenScenario) -> DomainResult:
    """classify -> attribute -> rank, with the checkpoints placed by hand."""
    scores: list[RouteScore] = []
    adjusted: dict[str, list[bool]] = {}
    intervals = owned_intervals(CHECKPOINT_MILES, ROUTE_MI)
    for rid, gr in scenario.routes.items():
        results = [
            classify_checkpoint(
                weather_sample(w, DEPARTURE + timedelta(hours=i)), scenario.load_lb, "gust"
            )
            for i, w in enumerate(gr.weather)
        ]
        adjusted[rid] = [r.load_adjusted for r in results]
        stats = route_stats(intervals, [r.overall for r in results])
        scores.append(RouteScore(route_id=rid, duration_s=gr.minutes * 60.0, stats=stats))
    rec, ranked = recommend(scores)
    return DomainResult(rec, [r.route_id for r in ranked], adjusted)
