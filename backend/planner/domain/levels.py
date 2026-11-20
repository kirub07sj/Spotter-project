"""Risk levels and every threshold constant (D-01, D-03). The only place these numbers live."""

from enum import IntEnum
from typing import Final, Literal

WindMetric = Literal["gust", "sustained"]
Factor = Literal["wind", "snow", "rain"]


class Level(IntEnum):
    UNKNOWN = -1  # weather missing; excluded from stats, never treated as safe
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4


KNOWN_LEVELS: Final = (Level.LOW, Level.MODERATE, Level.HIGH, Level.SEVERE, Level.NO_TRAVEL)

# Lower bounds are inclusive (D-01).
WIND_MODERATE_MPH: Final = 25.0
WIND_HIGH_MPH: Final = 35.0
WIND_SEVERE_MPH: Final = 45.0
WIND_NO_TRAVEL_MPH: Final = 55.0  # inclusive: >= 55 is No Travel

RAIN_MODERATE_IN_HR: Final = 0.10
RAIN_HIGH_IN_HR: Final = 0.25
RAIN_SEVERE_IN_HR: Final = 0.50
RAIN_NO_TRAVEL_ABOVE_IN_HR: Final = 1.00  # strict: 1.00 itself is Severe

SNOW_MODERATE_IN_HR: Final = 0.5
SNOW_HIGH_IN_HR: Final = 1.0
SNOW_SEVERE_IN_HR: Final = 2.0
SNOW_NO_TRAVEL_ABOVE_IN_HR: Final = 3.0  # strict: 3.0 itself is Severe

# Load rules (D-03): cargo weight in lb, strict comparisons, wind only.
LOAD_WIND_NO_TRAVEL_ABOVE_LB: Final = 30_000  # with wind in the Severe band (45-54)
LOAD_WIND_SEVERE_ABOVE_LB: Final = 40_000  # with wind in the High band (35-44)

WIND_BANDS: Final = (WIND_MODERATE_MPH, WIND_HIGH_MPH, WIND_SEVERE_MPH)
RAIN_BANDS: Final = (RAIN_MODERATE_IN_HR, RAIN_HIGH_IN_HR, RAIN_SEVERE_IN_HR)
SNOW_BANDS: Final = (SNOW_MODERATE_IN_HR, SNOW_HIGH_IN_HR, SNOW_SEVERE_IN_HR)
