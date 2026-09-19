# AI Project Planner — local development helpers
# Requires: Python 3.11+, Node 20+ (nvm recommended)

.PHONY: help install backend-install frontend-install backend-run frontend-run backend-test frontend-build frontend-lint migrate seed docker-up docker-down static

help:
	@echo "Targets:"
	@echo "  make install          - install backend + frontend deps"
	@echo "  make backend-run      - start FastAPI on :8000"
	@echo "  make frontend-run     - start Vite on :5173"
	@echo "  make backend-test     - run pytest"
	@echo "  make frontend-build   - production build"
	@echo "  make static           - build UI into backend/static"
	@echo "  make frontend-lint    - ESLint"
	@echo "  make migrate          - alembic upgrade head"
	@echo "  make seed             - load demo plan (~20 tasks)"
	@echo "  make docker-up        - full app (UI+API) via Docker"

install: backend-install frontend-install

backend-install:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -e ".[dev]"

frontend-install:
	cd frontend && npm install

backend-run:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend-run:
	cd frontend && npm run dev

backend-test:
	cd backend && . .venv/bin/activate && pytest -q

frontend-build:
	cd frontend && npm run build

static: frontend-build
	rm -rf backend/static && mkdir -p backend/static && cp -R frontend/dist/* backend/static/

frontend-lint:
	cd frontend && npm run lint

migrate:
	cd backend && . .venv/bin/activate && alembic upgrade head

seed:
	cd backend && . .venv/bin/activate && python -m app.seed

docker-up:
	docker compose up --build

docker-down:
	docker compose down
