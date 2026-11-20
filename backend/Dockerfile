# For Fly.io / Railway / any container host. Render can use render.yaml instead.
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy \
    DJANGO_SETTINGS_MODULE=config.settings.prod
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
ARG GIT_SHA=unknown
ENV GIT_SHA=$GIT_SHA
# collectstatic needs a secret key to import prod settings; it is not used at runtime.
RUN DJANGO_SECRET_KEY=build-only uv run --no-dev python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["sh", "-c", "uv run --no-dev gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:${PORT:-8000} --timeout 30"]
