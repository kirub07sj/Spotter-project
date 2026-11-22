from django.urls import include, path

from planner.api.views import HealthView

urlpatterns = [
    path("", HealthView.as_view(), name="root-health"),
    path("api/v1/", include("planner.api.urls")),
]
