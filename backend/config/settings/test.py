from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = "test-secret"
ALLOWED_HOSTS = ["testserver", "localhost"]
PROVIDERS = "fake"
MAPBOX_TOKEN = "pk.test-token"
TRUCK_MAX_SPEED_MPH = 65.0
RISK_WIND_METRIC = "gust"
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_RATES": {"plans": "1000/min", "heatmaps": "1000/min", "geocode": "1000/min"},
}
