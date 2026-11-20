SHELL := /bin/bash
.DEFAULT_GOAL := help
BACKEND := backend
FRONTEND := frontend

.PHONY: help install dev-backend dev-frontend schema check check-backend check-frontend check-schema coverage

help: ## List targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-16s %s\n", $$1, $$2}'

install: ## Install backend and frontend dependencies
	cd $(BACKEND) && uv sync
	cd $(FRONTEND) && pnpm install

dev-backend: ## Django dev server on :8000
	cd $(BACKEND) && uv run python manage.py runserver 8000

dev-frontend: ## Vite dev server on :5173 (proxies /api to :8000)
	cd $(FRONTEND) && pnpm dev

schema: ## Regenerate openapi.yaml and frontend types
	cd $(BACKEND) && uv run python manage.py spectacular --validate --fail-on-warn --file ../$(FRONTEND)/openapi.yaml
	cd $(FRONTEND) && pnpm gen:api

check: check-backend check-schema check-frontend ## Everything CI runs
	@echo "make check: all green"

check-backend: ## Lint, types, import rules, tests with coverage
	cd $(BACKEND) && uv run ruff check .
	cd $(BACKEND) && uv run ruff format --check .
	cd $(BACKEND) && uv run mypy planner config
	cd $(BACKEND) && uv run lint-imports
	cd $(BACKEND) && uv run pytest -q --cov --cov-report=term --cov-fail-under=0
	cd $(BACKEND) && uv run coverage report --include='planner/domain/*' --fail-under=90 > /dev/null

check-schema: ## Fail if openapi.yaml or schema.d.ts are stale
	cd $(BACKEND) && uv run python manage.py spectacular --validate --fail-on-warn --file /tmp/openapi.check.yaml
	diff -q /tmp/openapi.check.yaml $(FRONTEND)/openapi.yaml
	cd $(FRONTEND) && npx openapi-typescript openapi.yaml -o /tmp/schema.check.d.ts >/dev/null && npx prettier --stdin-filepath src/api/schema.d.ts < /tmp/schema.check.d.ts | diff -q - src/api/schema.d.ts

check-frontend: ## Lint, typecheck, unit tests, build, bundle budget
	cd $(FRONTEND) && pnpm lint
	cd $(FRONTEND) && pnpm typecheck
	cd $(FRONTEND) && pnpm test
	cd $(FRONTEND) && pnpm build
	cd $(FRONTEND) && pnpm size

coverage: ## Branch coverage for the grading-critical modules
	cd $(BACKEND) && uv run pytest -q --cov --cov-report=term-missing:skip-covered planner/tests/domain >/dev/null; \
	uv run coverage report --include='planner/domain/risk.py,planner/domain/ranking.py'
