from datetime import UTC, datetime, timedelta

import pytest

from planner.domain.models import HourlySeries
from planner.domain.weather_lookup import bucket_time, sample_for

T0 = datetime(2026, 11, 20, 13, 0, tzinfo=UTC)


def series(n: int = 5, *, gust_at: dict[int, float | None] | None = None) -> HourlySeries:
    start = int(T0.timestamp())
    gusts: list[float | None] = [float(10 + i) for i in range(n)]
    for i, v in (gust_at or {}).items():
        gusts[i] = v
    return HourlySeries(
        times=tuple(start + 3600 * i for i in range(n)),
        wind_mph=tuple(float(i) for i in range(n)),
        gust_mph=tuple(gusts),
        rain_in_hr=tuple(0.01 * i for i in range(n)),
        snow_in_hr=tuple(0.1 * i for i in range(n)),
    )


@pytest.mark.parametrize(
    ("eta", "bucket"),
    [
        (T0, T0),  # exactly on the hour: use T (D-08)
        (T0 + timedelta(seconds=1), T0 + timedelta(hours=1)),
        (T0 + timedelta(minutes=21), T0 + timedelta(hours=1)),  # ceil, not floor
        (T0 + timedelta(minutes=59, seconds=59), T0 + timedelta(hours=1)),
        (T0 + timedelta(microseconds=1), T0 + timedelta(hours=1)),
    ],
)
def test_bucket_is_ceil_hour(eta: datetime, bucket: datetime) -> None:
    assert bucket_time(eta) == bucket


def test_sample_for_picks_ceil_bucket() -> None:
    ws = sample_for(series(), T0 + timedelta(hours=1, minutes=21))
    assert ws.forecast_hour == T0 + timedelta(hours=2)
    assert ws.gust_mph == 12.0 and ws.wind_mph == 2.0
    assert ws.rain_in_hr == pytest.approx(0.02) and ws.snow_in_hr == pytest.approx(0.2)


def test_eta_before_series_start_clamps_to_first_hour() -> None:
    # Departure up to 1 h in the past: the past hour isn't available (docs/03 §13).
    ws = sample_for(series(), T0 - timedelta(minutes=40))
    assert ws.forecast_hour == T0
    assert ws.gust_mph == 10.0


def test_eta_after_series_end_is_missing() -> None:
    ws = sample_for(series(3), T0 + timedelta(hours=5))
    assert ws.gust_mph is None and ws.is_complete is False


def test_null_values_stay_missing() -> None:
    ws = sample_for(series(gust_at={1: None}), T0 + timedelta(hours=1))
    assert ws.gust_mph is None


def test_irregular_series_is_rejected() -> None:
    s = series()
    broken = HourlySeries(
        times=(s.times[0], s.times[0] + 1800, *s.times[2:]),
        wind_mph=s.wind_mph,
        gust_mph=s.gust_mph,
        rain_in_hr=s.rain_in_hr,
        snow_in_hr=s.snow_in_hr,
    )
    ws = sample_for(broken, T0 + timedelta(hours=1))
    assert ws.gust_mph is None  # never guess when the timestamp doesn't line up


def test_bucket_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="aware"):
        bucket_time(datetime(2026, 1, 1))


def test_floor_hour() -> None:
    from planner.domain.weather_lookup import floor_hour

    assert floor_hour(T0 + timedelta(minutes=59)) == T0
