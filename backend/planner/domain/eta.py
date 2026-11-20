"""ETA with the truck speed cap (D-07)."""

from collections.abc import Sequence

from .geo import cumulative
from .units import mph_to_mps

__all__ = ["capped_durations", "cumulative"]


def capped_durations(
    seg_dist_m: Sequence[float], seg_dur_s: Sequence[float], cap_mph: float
) -> tuple[float, ...]:
    """No segment is driven faster than the cap. Car routing engines assume car speeds."""
    if cap_mph <= 0:
        return tuple(seg_dur_s)
    cap_mps = mph_to_mps(cap_mph)
    return tuple(max(t, d / cap_mps) for d, t in zip(seg_dist_m, seg_dur_s, strict=True))
