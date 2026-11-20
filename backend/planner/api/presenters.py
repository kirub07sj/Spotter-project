"""Turns service results into the JSON contract. Plain dicts keep large plans fast;
contract tests check the output against the response serializers."""

from datetime import UTC, datetime
from typing import Any

from planner.domain.levels import KNOWN_LEVELS
from planner.services.plan_service import Plan, PlannedCheckpoint, PlannedRoute


def iso(t: datetime) -> str:
    return t.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _r(value: float | None, digits: int) -> float | None:
    return None if value is None else round(value, digits)


def _checkpoint(pc: PlannedCheckpoint) -> dict[str, Any]:
    cp, ws, risk = pc.checkpoint, pc.weather, pc.risk
    return {
        "index": cp.index,
        "mile": round(cp.mile, 2),
        "lat": round(cp.position.lat, 5),
        "lon": round(cp.position.lon, 5),
        "eta": iso(cp.eta),
        "forecast_hour": iso(ws.forecast_hour),
        "weather": {
            "wind_mph": _r(ws.wind_mph, 1),
            "gust_mph": _r(ws.gust_mph, 1),
            "rain_in_hr": _r(ws.rain_in_hr, 3),
            "snow_in_hr": _r(ws.snow_in_hr, 3),
        },
        "levels": {
            "wind": risk.wind.name,
            "rain": risk.rain.name,
            "snow": risk.snow.name,
            "overall": risk.overall.name,
        },
        "dominant_factor": risk.dominant_factor,
        "load_adjusted": risk.load_adjusted,
        "owned_mi": round(pc.owned_mi, 2),
        "low_confidence": pc.low_confidence,
    }


def _route(r: PlannedRoute) -> dict[str, Any]:
    return {
        "id": r.id,
        "label": r.label,
        "source": r.source,
        "distance_mi": round(r.distance_mi, 1),
        "duration_s": round(r.duration_s),
        "arrival_time": iso(r.arrival),
        "geometry": r.geometry,
        "cum_time_s": r.cum_time_s,
        "risk_segments": [
            {
                "level": s.run.level.name,
                "from_mi": round(s.run.from_mi, 2),
                "to_mi": round(s.run.to_mi, 2),
                "geometry": s.geometry,
            }
            for s in r.segments
        ],
        "checkpoints": [_checkpoint(c) for c in r.checkpoints],
        "stats": {
            "miles_by_level": {
                lvl.name: round(r.stats.miles_by_level[lvl], 1) for lvl in KNOWN_LEVELS
            },
            "unknown_mi": round(r.stats.unknown_mi, 1),
            "avg_risk": round(r.stats.avg_risk, 2),
            "max_level": r.stats.max_level.name,
        },
        "rank": r.rank,
        "recommended": r.recommended,
    }


def present_plan(plan: Plan) -> dict[str, Any]:
    req, cfg = plan.request, plan.config
    return {
        "plan_id": plan.plan_id,
        "generated_at": iso(plan.generated_at),
        "assumptions": {
            "wind_metric": cfg.wind_metric,
            "truck_max_speed_mph": cfg.truck_max_speed_mph,
            "hos_breaks": False,  # D-07
            "scenario": req.scenario,
            "providers": cfg.providers_name,
            "load_weight_lb": req.load_lb,
            "sample_interval_mi": req.interval_mi,
            "departure_time": iso(req.departure),
        },
        "routes": [_route(r) for r in sorted(plan.routes, key=lambda r: r.id)],
        "recommendation": {
            "route_id": plan.recommendation.route_id,
            "status": plan.recommendation.status,
            "reasons": list(plan.recommendation.reasons),
        },
        "warnings": [{"code": w.code, "detail": w.detail} for w in plan.warnings],
    }
