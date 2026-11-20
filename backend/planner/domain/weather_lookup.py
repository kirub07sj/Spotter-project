"""Pick the forecast hour for an ETA (D-08)."""

from datetime import UTC, datetime, timedelta

from .models import HourlySeries, WeatherSample

HOUR_S = 3600


def bucket_time(eta: datetime) -> datetime:
    """A value stamped T covers (T - 1h, T], so use ceil_to_hour(eta) (D-08)."""
    if eta.tzinfo is None:
        raise ValueError("eta must be timezone-aware")
    eta = eta.astimezone(UTC)
    floor = eta.replace(minute=0, second=0, microsecond=0)
    return floor if eta == floor else floor + timedelta(hours=1)


def floor_hour(t: datetime) -> datetime:
    return t.astimezone(UTC).replace(minute=0, second=0, microsecond=0)


def sample_for(series: HourlySeries, eta: datetime) -> WeatherSample:
    bucket = bucket_time(eta)
    target = int(bucket.timestamp())
    first = series.times[0]
    # Departure up to an hour in the past: that hour isn't served, so clamp to the first.
    i = max(0, (target - first) // HOUR_S)
    if i >= len(series.times) or series.times[i] != max(target, first):
        return WeatherSample(None, None, None, None, forecast_hour=bucket)
    return WeatherSample(
        wind_mph=series.wind_mph[i],
        gust_mph=series.gust_mph[i],
        rain_in_hr=series.rain_in_hr[i],
        snow_in_hr=series.snow_in_hr[i],
        forecast_hour=datetime.fromtimestamp(series.times[i], tz=UTC),
    )
