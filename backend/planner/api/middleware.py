import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from planner.logging import request_id_var


class RequestContextMiddleware:
    """Assigns a request id for log correlation and echoes it back as X-Request-ID."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        incoming = request.headers.get("X-Request-ID", "")
        rid = incoming[:64] if incoming.isprintable() and incoming else uuid.uuid4().hex[:16]
        token = request_id_var.set(rid)
        try:
            response = self.get_response(request)
        finally:
            request_id_var.reset(token)
        response["X-Request-ID"] = rid
        return response
