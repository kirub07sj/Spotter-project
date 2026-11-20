"""Typed errors raised by domain, providers and services; api/errors.py maps them to
problem+json (docs/02 §4)."""


class PlannerError(Exception):
    code = "PLANNER_ERROR"
    status = 500
    title = "Planning failed"


class NoRouteError(PlannerError):
    code, status, title = "NO_ROUTE", 422, "No route found"


class RouteTooLongError(PlannerError):
    code, status, title = "ROUTE_TOO_LONG", 422, "Route too long"


class GeocodeNotFoundError(PlannerError):
    code, status, title = "GEOCODE_NOT_FOUND", 404, "Place not found"


class ProviderUnavailableError(PlannerError):
    code, status, title = "PROVIDER_UNAVAILABLE", 503, "Provider unavailable"
