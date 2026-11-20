"""Mile attribution (D-09), route stats (D-10) and risk runs for the map."""

from collections.abc import Sequence

from .levels import KNOWN_LEVELS, Level
from .models import RiskRun, RouteStats

Interval = tuple[float, float]


def owned_intervals(miles: Sequence[float], total_mi: float) -> list[Interval]:
    """Each checkpoint owns the road from the midpoint with its previous neighbour to the
    midpoint with its next one; the ends own up to the route ends."""
    if not miles:
        raise ValueError("at least one checkpoint is required")
    last = len(miles) - 1
    out = []
    for i, m in enumerate(miles):
        left = 0.0 if i == 0 else (miles[i - 1] + m) / 2
        right = total_mi if i == last else (m + miles[i + 1]) / 2
        out.append((left, right))
    return out


def route_stats(intervals: Sequence[Interval], levels: Sequence[Level]) -> RouteStats:
    if len(intervals) != len(levels):
        raise ValueError("one level per interval is required")
    by_level = dict.fromkeys(KNOWN_LEVELS, 0.0)
    unknown = weighted = known = 0.0
    for (left, right), level in zip(intervals, levels, strict=True):
        miles = right - left
        if level is Level.UNKNOWN:
            unknown += miles  # excluded from stats; never counted as Low
            continue
        by_level[level] += miles
        weighted += miles * int(level)
        known += miles
    present = [lvl for lvl in levels if lvl is not Level.UNKNOWN]
    return RouteStats(
        miles_by_level=by_level,
        avg_risk=weighted / known if known else 0.0,
        max_level=max(present, default=Level.UNKNOWN),
        unknown_mi=unknown,
    )


def risk_runs(intervals: Sequence[Interval], levels: Sequence[Level]) -> list[RiskRun]:
    """Merge neighbouring intervals that share a level into (from_mi, to_mi, level) runs."""
    runs: list[RiskRun] = []
    for (left, right), level in zip(intervals, levels, strict=True):
        if runs and runs[-1].level is level:
            runs[-1] = RiskRun(runs[-1].from_mi, right, level)
        else:
            runs.append(RiskRun(left, right, level))
    return runs
