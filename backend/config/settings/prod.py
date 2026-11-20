from .base import *  # noqa: F403
from .base import SECRET_KEY, env_bool

if SECRET_KEY.startswith("dev-insecure"):
    raise RuntimeError("DJANGO_SECRET_KEY must be set in production")

DEBUG = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
SECURE_REDIRECT_EXEMPT = [r"^api/v1/health$"]
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
STORAGES = {
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
MIDDLEWARE = [
    MIDDLEWARE[0],  # noqa: F405
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[1:],  # noqa: F405
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
SILENCED_SYSTEM_CHECKS = [
    # Stateless JSON API: no cookies, sessions or form posts, so CSRF middleware has nothing
    # to protect; CORS is an allowlist (docs/02 §8).
    "security.W003",
    # HSTS subdomains/preload depend on the host's domain (e.g. *.onrender.com); decide per
    # deployment rather than here.
    "security.W005",
    "security.W021",
]
