from asgiref.sync import async_to_sync
from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from planner.domain.errors import GeocodeNotFoundError
from planner.domain.models import LatLon
from planner.domain.scenarios import SCENARIOS
from planner.providers.registry import get_providers
from planner.services.plan_service import PlanConfig, PlanRequest, create_plan
from planner.services.timing import Timings

from .presenters import present_plan
from .serializers import (
    GeocodeQuerySerializer,
    GeocodeResponseSerializer,
    PlanRequestSerializer,
    PlanResponseSerializer,
    ProblemSerializer,
    ScenarioQuerySerializer,
)

PROBLEM_RESPONSES = {code: ProblemSerializer for code in (400, 404, 422, 429, 503)}


class HealthView(APIView):
    @extend_schema(
        responses=inline_serializer(
            "Health", {"status": serializers.CharField(), "version": serializers.CharField()}
        )
    )
    def get(self, request: Request) -> Response:
        return Response({"status": "ok", "version": settings.APP_VERSION})


class GeocodeView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "geocode"

    @extend_schema(
        parameters=[GeocodeQuerySerializer],
        responses={200: GeocodeResponseSerializer, **PROBLEM_RESPONSES},
    )
    def get(self, request: Request) -> Response:
        query = GeocodeQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        places = async_to_sync(get_providers().geocoding.search)(
            query.validated_data["q"], query.validated_data["limit"]
        )
        if not places:
            raise GeocodeNotFoundError(f"No places match “{query.validated_data['q']}”.")
        results = [
            {"id": p.id, "label": p.label, "lat": p.position.lat, "lon": p.position.lon}
            for p in places
        ]
        return Response({"results": results})


def plan_config() -> PlanConfig:
    return PlanConfig(
        wind_metric="sustained" if settings.RISK_WIND_METRIC == "sustained" else "gust",
        truck_max_speed_mph=settings.TRUCK_MAX_SPEED_MPH,
        providers_name=get_providers().name,
    )


class PlanView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "plans"

    @extend_schema(
        request=PlanRequestSerializer,
        parameters=[OpenApiParameter("scenario", str, enum=list(SCENARIOS), required=False)],
        responses={200: PlanResponseSerializer, **PROBLEM_RESPONSES},
    )
    def post(self, request: Request) -> Response:
        now = timezone.now()
        body = PlanRequestSerializer(data=request.data, context={"now": now})
        body.is_valid(raise_exception=True)
        query = ScenarioQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = body.validated_data
        plan_request = PlanRequest(
            origin=LatLon(data["origin"]["lat"], data["origin"]["lon"]),
            destination=LatLon(data["destination"]["lat"], data["destination"]["lon"]),
            departure=data["departure_time"],
            load_lb=data["load_weight_lb"],
            interval_mi=int(data["sample_interval_mi"]),
            scenario=query.validated_data.get("scenario"),
        )
        timings = Timings()
        plan = async_to_sync(create_plan)(
            plan_request, get_providers(), plan_config(), now, timings
        )
        with timings.measure("serialize"):
            payload = present_plan(plan)
        response = Response(payload)
        response["Server-Timing"] = timings.header()
        return response
