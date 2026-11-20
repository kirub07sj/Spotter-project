"""Request validation (D-17) and response shapes. The response serializers define the
OpenAPI schema the frontend types are generated from; contract tests validate real
responses against them."""

from datetime import datetime, timedelta
from typing import Any

from rest_framework import serializers

from planner.domain.geo import haversine_m
from planner.domain.levels import Level
from planner.domain.models import LatLon
from planner.domain.scenarios import SCENARIOS
from planner.domain.units import mi_to_m

LEVEL_CHOICES = [lvl.name for lvl in sorted(Level, key=int)]
KNOWN_LEVEL_CHOICES = [lvl.name for lvl in sorted(Level, key=int) if lvl is not Level.UNKNOWN]
INTERVAL_CHOICES = [10, 25, 50]
MIN_SEPARATION_MI = 0.1
DEPARTURE_PAST = timedelta(hours=1)
DEPARTURE_FUTURE = timedelta(days=7)
MAX_LOAD_LB = 80_000


# --- requests ---


class PointSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)
    label = serializers.CharField(max_length=200, required=False, allow_blank=True)


class PlanRequestSerializer(serializers.Serializer):
    origin = PointSerializer()
    destination = PointSerializer()
    departure_time = serializers.DateTimeField()
    load_weight_lb = serializers.IntegerField(min_value=1, max_value=MAX_LOAD_LB)
    sample_interval_mi = serializers.ChoiceField(choices=INTERVAL_CHOICES, default=25)

    def validate_departure_time(self, value: datetime) -> datetime:
        now: datetime = self.context["now"]
        if value < now - DEPARTURE_PAST:
            raise serializers.ValidationError("Departure can be at most 1 hour in the past.")
        if value > now + DEPARTURE_FUTURE:
            raise serializers.ValidationError("Departure can be at most 7 days ahead.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        o, d = attrs["origin"], attrs["destination"]
        if haversine_m(LatLon(o["lat"], o["lon"]), LatLon(d["lat"], d["lon"])) < mi_to_m(
            MIN_SEPARATION_MI
        ):
            raise serializers.ValidationError("Origin and destination must be different.")
        return attrs


class ScenarioQuerySerializer(serializers.Serializer):
    scenario = serializers.ChoiceField(choices=list(SCENARIOS), required=False)


class GeocodeQuerySerializer(serializers.Serializer):
    q = serializers.CharField(min_length=2, max_length=200, trim_whitespace=True)
    limit = serializers.IntegerField(min_value=1, max_value=10, default=5)


# --- responses ---


class PlaceSerializer(serializers.Serializer):
    id = serializers.CharField()
    label = serializers.CharField()
    lat = serializers.FloatField()
    lon = serializers.FloatField()


class GeocodeResponseSerializer(serializers.Serializer):
    results = PlaceSerializer(many=True)


class AssumptionsSerializer(serializers.Serializer):
    wind_metric = serializers.ChoiceField(choices=["gust", "sustained"])
    truck_max_speed_mph = serializers.FloatField()
    hos_breaks = serializers.BooleanField()
    scenario = serializers.ChoiceField(choices=list(SCENARIOS), allow_null=True)
    providers = serializers.ChoiceField(choices=["real", "fake"])
    load_weight_lb = serializers.IntegerField()
    sample_interval_mi = serializers.IntegerField()
    departure_time = serializers.DateTimeField()


class WeatherSerializer(serializers.Serializer):
    wind_mph = serializers.FloatField(allow_null=True)
    gust_mph = serializers.FloatField(allow_null=True)
    rain_in_hr = serializers.FloatField(allow_null=True)
    snow_in_hr = serializers.FloatField(allow_null=True)


class CheckpointLevelsSerializer(serializers.Serializer):
    wind = serializers.ChoiceField(choices=LEVEL_CHOICES)
    rain = serializers.ChoiceField(choices=LEVEL_CHOICES)
    snow = serializers.ChoiceField(choices=LEVEL_CHOICES)
    overall = serializers.ChoiceField(choices=LEVEL_CHOICES)


class CheckpointSerializer(serializers.Serializer):
    index = serializers.IntegerField()
    mile = serializers.FloatField()
    lat = serializers.FloatField()
    lon = serializers.FloatField()
    eta = serializers.DateTimeField()
    forecast_hour = serializers.DateTimeField()
    weather = WeatherSerializer()
    levels = CheckpointLevelsSerializer()
    dominant_factor = serializers.ChoiceField(choices=["wind", "snow", "rain"], allow_null=True)
    load_adjusted = serializers.BooleanField()
    owned_mi = serializers.FloatField()
    low_confidence = serializers.BooleanField()


class RiskSegmentSerializer(serializers.Serializer):
    level = serializers.ChoiceField(choices=LEVEL_CHOICES)
    from_mi = serializers.FloatField()
    to_mi = serializers.FloatField()
    geometry = serializers.CharField(help_text="polyline6")


class MilesByLevelSerializer(serializers.Serializer):
    LOW = serializers.FloatField()
    MODERATE = serializers.FloatField()
    HIGH = serializers.FloatField()
    SEVERE = serializers.FloatField()
    NO_TRAVEL = serializers.FloatField()


class RouteStatsSerializer(serializers.Serializer):
    miles_by_level = MilesByLevelSerializer()
    unknown_mi = serializers.FloatField()
    avg_risk = serializers.FloatField()
    max_level = serializers.ChoiceField(choices=LEVEL_CHOICES)


class RouteSerializer(serializers.Serializer):
    id = serializers.ChoiceField(choices=["A", "B", "C"])
    label = serializers.CharField()
    source = serializers.ChoiceField(choices=["provider", "via"])
    distance_mi = serializers.FloatField()
    duration_s = serializers.FloatField()
    arrival_time = serializers.DateTimeField()
    geometry = serializers.CharField(help_text="polyline6, simplified to <= 2,000 vertices")
    cum_time_s = serializers.ListField(
        child=serializers.FloatField(), help_text="Seconds from departure, one per vertex"
    )
    risk_segments = RiskSegmentSerializer(many=True)
    checkpoints = CheckpointSerializer(many=True)
    stats = RouteStatsSerializer()
    rank = serializers.IntegerField(min_value=1)
    recommended = serializers.BooleanField()


class RecommendationSerializer(serializers.Serializer):
    route_id = serializers.ChoiceField(choices=["A", "B", "C"])
    status = serializers.ChoiceField(choices=["OK", "NO_SAFE_ROUTE"])
    reasons = serializers.ListField(child=serializers.CharField())


class WarningSerializer(serializers.Serializer):
    code = serializers.ChoiceField(
        choices=[
            "ONLY_N_DISTINCT_ROUTES",
            "WEATHER_GAPS",
            "LOW_CONFIDENCE_FORECAST",
            "SIMULATED_WEATHER",
        ]
    )
    detail = serializers.CharField()


class PlanResponseSerializer(serializers.Serializer):
    plan_id = serializers.CharField()
    generated_at = serializers.DateTimeField()
    assumptions = AssumptionsSerializer()
    routes = RouteSerializer(many=True)
    recommendation = RecommendationSerializer()
    warnings = WarningSerializer(many=True)


class ProblemSerializer(serializers.Serializer):
    type = serializers.CharField()
    title = serializers.CharField()
    status = serializers.IntegerField()
    code = serializers.ChoiceField(
        choices=[
            "VALIDATION_ERROR",
            "GEOCODE_NOT_FOUND",
            "NO_ROUTE",
            "ROUTE_TOO_LONG",
            "PROVIDER_UNAVAILABLE",
            "RATE_LIMITED",
            "HTTP_ERROR",
        ]
    )
    detail = serializers.CharField()


# Named enums for drf-spectacular (ENUM_NAME_OVERRIDES wants (value, label) pairs).
LEVEL_ENUM = [(v, v) for v in LEVEL_CHOICES]
INTERVAL_ENUM = [(v, str(v)) for v in INTERVAL_CHOICES]
ROUTE_ID_ENUM = [(v, v) for v in ("A", "B", "C")]
