"""Checkpoint positions and ETAs (D-06, docs/03 §5)."""

from bisect import bisect_right
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from .geo import lerp
from .models import Checkpoint, LatLon
from .units import M_PER_MI

# D-06: a regular checkpoint closer than this to the destination is dropped.
MIN_GAP_BEFORE_DESTINATION_MI = 0.5


def checkpoint_miles(total_mi: float, interval_mi: float) -> list[float]:
    miles = [0.0]
    m = float(interval_mi)
    # D-06: dropped only when *less than* 0.5 mi before the destination, so exactly 0.5 stays.
    while m <= total_mi - MIN_GAP_BEFORE_DESTINATION_MI:
        miles.append(m)
        m += interval_mi
    miles.append(total_mi)
    return miles


def locate(
    cum_dist_m: Sequence[float],
    cum_dur_s: Sequence[float],
    coords: Sequence[LatLon],
    target_m: float,
) -> tuple[LatLon, float]:
    """Point and elapsed seconds at `target_m` along the route. O(log n)."""
    i = bisect_right(cum_dist_m, target_m) - 1
    i = min(max(i, 0), len(coords) - 2)
    seg = cum_dist_m[i + 1] - cum_dist_m[i]
    f = 0.0 if seg == 0 else (target_m - cum_dist_m[i]) / seg
    t = cum_dur_s[i] + f * (cum_dur_s[i + 1] - cum_dur_s[i])
    return lerp(coords[i], coords[i + 1], f), t


def sample_checkpoints(
    coords: Sequence[LatLon],
    cum_dist_m: Sequence[float],
    cum_dur_s: Sequence[float],
    departure: datetime,
    interval_mi: float,
) -> list[Checkpoint]:
    if departure.tzinfo is None:
        raise ValueError("departure must be timezone-aware")
    departure_utc = departure.astimezone(UTC)
    total_mi = cum_dist_m[-1] / M_PER_MI
    out = []
    for idx, mile in enumerate(checkpoint_miles(total_mi, interval_mi)):
        point, elapsed_s = locate(cum_dist_m, cum_dur_s, coords, mile * M_PER_MI)
        eta = departure_utc + timedelta(seconds=elapsed_s)
        out.append(Checkpoint(index=idx, mile=mile, position=point, eta=eta))
    return out
