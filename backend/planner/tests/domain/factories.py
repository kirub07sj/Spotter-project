"""Small builders shared by the domain tests."""

from datetime import UTC, datetime

from planner.domain.models import WeatherSample

T0 = datetime(2026, 11, 20, 13, 0, tzinfo=UTC)


def sample(
    *,
    wind: float | None = 0.0,
    gust: float | None = 0.0,
    rain: float | None = 0.0,
    snow: float | None = 0.0,
    hour: datetime = T0,
) -> WeatherSample:
    return WeatherSample(
        wind_mph=wind, gust_mph=gust, rain_in_hr=rain, snow_in_hr=snow, forecast_hour=hour
    )
