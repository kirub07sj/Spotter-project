import pytest

from planner.domain.levels import Level
from planner.domain.models import RouteStats
from planner.domain.ranking import RouteScore, explain, ranking_key, recommend


def stats(
    nt: float = 0.0, sev: float = 0.0, high: float = 0.0, avg: float = 0.0, low: float = 0.0
) -> RouteStats:
    by_level = {
        Level.LOW: low,
        Level.MODERATE: 0.0,
        Level.HIGH: high,
        Level.SEVERE: sev,
        Level.NO_TRAVEL: nt,
    }
    present = [lvl for lvl, mi in by_level.items() if mi > 0]
    return RouteStats(
        miles_by_level=by_level,
        avg_risk=avg,
        max_level=max(present, default=Level.LOW),
        unknown_mi=0.0,
    )


def route(rid: str, minutes: float, **kw: float) -> RouteScore:
    return RouteScore(route_id=rid, duration_s=minutes * 60, stats=stats(**kw))


def test_key_order_is_no_travel_severe_high_avg_minutes_id() -> None:
    r = route("B", 125.4, nt=1.04, sev=2.06, high=3.0, avg=0.123)
    assert ranking_key(r) == (1.0, 2.1, 3.0, 0.12, 125, "B")


def test_no_travel_beats_everything() -> None:
    a = route("A", 60, nt=0.5)
    b = route("B", 600, sev=500, high=500, avg=3.0)
    rec, ranked = recommend([a, b])
    assert [r.route_id for r in ranked] == ["B", "A"]
    assert rec.status == "OK"
    assert rec.reasons == ("Chosen over A: 0.5 fewer No Travel miles",)


def test_float_noise_does_not_decide() -> None:
    # D-11: 0.30000000004 must tie with 0.3 and fall through to duration.
    a = route("A", 100, avg=0.30000000004)
    b = route("B", 90, avg=0.3)
    rec, _ = recommend([a, b])
    assert rec.route_id == "B"
    assert rec.reasons == ("Chosen over A: same risk profile, 10 min faster",)


def test_duration_compared_in_whole_minutes() -> None:
    a = RouteScore("A", 6000.0, stats())
    b = RouteScore("B", 6010.0, stats())  # 100.17 min rounds to 100
    rec, ranked = recommend([b, a])
    assert [r.route_id for r in ranked] == ["A", "B"]
    assert rec.reasons == ("Tied with B on every criterion; listed first by route ID",)


def test_full_tie_breaks_by_id_deterministically() -> None:
    routes = [route("C", 100), route("A", 100), route("B", 100)]
    rec, ranked = recommend(routes)
    assert [r.route_id for r in ranked] == ["A", "B", "C"]
    assert rec.reasons == (
        "Tied with B on every criterion; listed first by route ID",
        "Tied with C on every criterion; listed first by route ID",
    )


def test_no_safe_route_when_best_has_no_travel() -> None:
    rec, _ = recommend([route("A", 100, nt=10), route("B", 100, nt=20)])
    assert rec.status == "NO_SAFE_ROUTE"
    assert rec.route_id == "A"


def test_single_route() -> None:
    rec, ranked = recommend([route("A", 100)])
    assert rec.route_id == "A" and rec.reasons == () and len(ranked) == 1


def test_empty_is_an_error() -> None:
    with pytest.raises(ValueError):
        recommend([])


@pytest.mark.parametrize(
    ("best", "other", "text"),
    [
        (
            route("A", 100, nt=5),
            route("B", 100, nt=7.5),
            "Chosen over B: 2.5 fewer No Travel miles",
        ),
        (route("A", 100, sev=10), route("B", 50, sev=35), "Chosen over B: 25.0 fewer Severe miles"),
        (
            route("A", 100, nt=5, sev=10),
            route("B", 50, nt=5, sev=35),
            "Chosen over B: same No Travel miles, 25.0 fewer Severe miles",
        ),
        (
            route("A", 100, sev=10, high=5),
            route("B", 50, sev=10, high=15),
            "Chosen over B: same Severe miles, 10.0 fewer High miles",
        ),
        (
            route("A", 100, high=5, avg=0.42),
            route("C", 50, high=5, avg=0.61),
            "Chosen over C: same Severe and High miles, lower average risk (0.42 vs 0.61)",
        ),
        (
            route("A", 100, nt=1, high=5, avg=0.42),
            route("C", 50, nt=1, high=5, avg=0.61),
            "Chosen over C: same No Travel, Severe and High miles, lower average risk "
            "(0.42 vs 0.61)",
        ),
        (route("A", 100), route("B", 118), "Chosen over B: same risk profile, 18 min faster"),
        (
            route("A", 100),
            route("B", 100),
            "Tied with B on every criterion; listed first by route ID",
        ),
    ],
)
def test_explain_describes_first_differing_key(
    best: RouteScore, other: RouteScore, text: str
) -> None:
    assert explain(best, other) == text


def test_explain_long_duration_difference_uses_hours() -> None:
    assert explain(route("A", 100), route("B", 225)) == (
        "Chosen over B: same risk profile, 2h 05m faster"
    )
