"""The only place unit conversions happen (AGENTS.md rule 5)."""

from typing import Final

KMH_PER_MPH: Final = 1.609344
MM_PER_IN: Final = 25.4
CM_PER_IN: Final = 2.54
M_PER_MI: Final = 1609.344
LB_PER_T: Final = 2204.62262
SECONDS_PER_HOUR: Final = 3600.0


def kmh_to_mph(v: float) -> float:
    return v / KMH_PER_MPH


def mm_to_in(v: float) -> float:
    """Rain and showers."""
    return v / MM_PER_IN


def cm_to_in(v: float) -> float:
    """Snowfall."""
    return v / CM_PER_IN


def m_to_mi(v: float) -> float:
    return v / M_PER_MI


def mi_to_m(v: float) -> float:
    return v * M_PER_MI


def km_to_m(v: float) -> float:
    return v * 1000.0


def lb_to_t(v: float) -> float:
    return v / LB_PER_T


def mph_to_mps(v: float) -> float:
    return v * M_PER_MI / SECONDS_PER_HOUR
