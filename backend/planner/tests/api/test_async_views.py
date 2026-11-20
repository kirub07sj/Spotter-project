from inspect import iscoroutinefunction

import pytest
from django.test import AsyncClient

from planner.api.views import GeocodeView, HealthView, HeatmapView, PlanView


@pytest.mark.parametrize(
    ("view", "method"),
    [(HealthView, "get"), (GeocodeView, "get"), (PlanView, "post"), (HeatmapView, "post")],
)
def test_api_handlers_are_native_async(view: type, method: str) -> None:
    assert iscoroutinefunction(getattr(view, method))


@pytest.mark.usefixtures("fake_providers")
async def test_asgi_health_errors_and_options() -> None:
    client = AsyncClient()
    health = await client.get("/api/v1/health")
    assert health.status_code == 200 and health.json()["status"] == "ok"
    invalid = await client.post("/api/v1/plans", {}, content_type="application/json")
    assert invalid.status_code == 400 and invalid.json()["code"] == "VALIDATION_ERROR"
    wrong_method = await client.delete("/api/v1/plans")
    assert wrong_method.status_code == 405
    options = await client.options("/api/v1/plans")
    assert options.status_code == 200 and "POST" in options["Allow"]
