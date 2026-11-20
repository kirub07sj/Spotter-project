"""Maps exceptions to RFC 7807 problem+json (docs/02 §4)."""

from typing import Any

from rest_framework import exceptions as drf_exc
from rest_framework.response import Response
from rest_framework.views import exception_handler

from planner.domain.errors import PlannerError


def problem(status: int, code: str, title: str, detail: str, **extra: Any) -> Response:
    body = {
        "type": f"https://errors.app/{code.lower().replace('_', '-')}",
        "title": title,
        "status": status,
        "code": code,
        "detail": detail,
        **extra,
    }
    return Response(body, status=status, content_type="application/problem+json")


def problem_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, PlannerError):
        # Messages are written by us; provider error text is never forwarded (docs/02 §8).
        return problem(exc.status, exc.code, exc.title, str(exc) or exc.title)
    if isinstance(exc, drf_exc.ValidationError):
        return problem(
            400, "VALIDATION_ERROR", "Invalid request", _first_error(exc.detail), errors=exc.detail
        )
    if isinstance(exc, drf_exc.Throttled):
        resp = problem(
            429, "RATE_LIMITED", "Too many requests", "Rate limit reached. Try again shortly."
        )
        if exc.wait:
            resp["Retry-After"] = str(int(exc.wait))
        return resp
    if isinstance(exc, drf_exc.ParseError):
        return problem(400, "VALIDATION_ERROR", "Invalid request", str(exc.detail))
    response = exception_handler(exc, context)
    if response is not None:
        detail = response.data.get("detail", "") if isinstance(response.data, dict) else ""
        return problem(response.status_code, "HTTP_ERROR", "Request failed", str(detail))
    return None


def _first_error(detail: Any) -> str:
    if isinstance(detail, dict):
        for key, value in detail.items():
            msg = _first_error(value)
            return msg if key == "non_field_errors" else f"{key}: {msg}"
    if isinstance(detail, list) and detail:
        return _first_error(detail[0])
    return str(detail)
