"""Ranking key (D-11), recommendation (D-12) and the reasons text."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from .levels import Level
from .models import RouteStats

Status = Literal["OK", "NO_SAFE_ROUTE"]
RiskKey = tuple[float, float, float, float, int]
RankingKey = tuple[float, float, float, float, int, str]


@dataclass(frozen=True, slots=True)
class RouteScore:
    route_id: str
    duration_s: float
    stats: RouteStats


@dataclass(frozen=True, slots=True)
class Recommendation:
    route_id: str
    status: Status
    reasons: tuple[str, ...]


def _risk_key(r: RouteScore) -> RiskKey:
    """Rounded before comparing so floating-point noise never decides (D-11)."""
    s = r.stats.miles_by_level
    return (
        round(s[Level.NO_TRAVEL], 1),
        round(s[Level.SEVERE], 1),
        round(s[Level.HIGH], 1),
        round(r.stats.avg_risk, 2),
        round(r.duration_s / 60),
    )


def ranking_key(r: RouteScore) -> RankingKey:
    """D-11 key, plus the id as the final tiebreaker so the result is deterministic."""
    return (*_risk_key(r), r.route_id)


def recommend(routes: Sequence[RouteScore]) -> tuple[Recommendation, list[RouteScore]]:
    if not routes:
        raise ValueError("at least one route is required")
    ranked = sorted(routes, key=ranking_key)
    best = ranked[0]
    status: Status = "NO_SAFE_ROUTE" if _risk_key(best)[0] > 0 else "OK"  # D-12
    reasons = tuple(explain(best, other) for other in ranked[1:])
    return Recommendation(route_id=best.route_id, status=status, reasons=reasons), ranked


def _join(names: list[str]) -> str:
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def _format_minutes(minutes: int) -> str:
    return f"{minutes} min" if minutes < 60 else f"{minutes // 60}h {minutes % 60:02d}m"


def explain(best: RouteScore, other: RouteScore) -> str:
    """Plain-words description of the first ranking key position where the two differ."""
    kb, ko = _risk_key(best), _risk_key(other)
    pos = next((i for i in range(5) if kb[i] != ko[i]), None)
    if pos is None:
        return f"Tied with {other.route_id} on every criterion; listed first by route ID"
    prefix = f"Chosen over {other.route_id}: "
    if pos == 4:
        return f"{prefix}same risk profile, {_format_minutes(ko[4] - kb[4])} faster"
    # Mention No Travel among the tied criteria only when the tie isn't at zero.
    tied = (["No Travel"] if kb[0] > 0 else []) + ["Severe", "High"][: max(pos - 1, 0)]
    same = f"same {_join(tied)} miles, " if pos > 0 and tied else ""
    if pos == 3:
        return f"{prefix}{same}lower average risk ({kb[3]:.2f} vs {ko[3]:.2f})"
    name = ("No Travel", "Severe", "High")[pos]
    return f"{prefix}{same}{ko[pos] - kb[pos]:.1f} fewer {name} miles"
