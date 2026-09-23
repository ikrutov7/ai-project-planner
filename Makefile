# AI Project Planner — local build + platform demo
# Requires: Python 3.11+, Node 20+ (nvm recommended), Docker (for demo-*)

.PHONY: help install backend-install frontend-install \
	backend-run frontend-run backend-test frontend-build frontend-lint \
	migrate seed excel static \
	build build-full check \
	docker-up docker-down \
	demo-package demo-build demo-up demo-down demo-logs demo-tunnel \
	demo-deploy-fly demo-deploy-render

ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
BACKEND := $(ROOT)/backend
FRONTEND := $(ROOT)/frontend
EXAMPLES := $(ROOT)/examples
SAMPLE_XLSX := $(EXAMPLES)/sample-plan.xlsx
DEMO_IMAGE := ai-project-planner:demo
DEMO_COMPOSE := $(ROOT)/docker-compose.demo.yml
VENV_PY := $(BACKEND)/.venv/bin/python

help:
	@echo ""
	@echo "══ Local (full build with seed data + Excel) ══"
	@echo "  make install          - backend + frontend deps"
	@echo "  make seed             - force-load demo plan (~20 tasks)"
	@echo "  make excel            - seed + regenerate examples/sample-plan.xlsx"
	@echo "  make static           - build UI into backend/static (+ sample Excel)"
	@echo "  make build            - install → migrate → seed/excel → static"
	@echo "  make build-full       - build + pytest + frontend lint"
	@echo "  make backend-run      - FastAPI :8000 (after build → UI+API)"
	@echo "  make frontend-run     - Vite :5173 (dev HMR)"
	@echo "  make check            - pytest + frontend production build"
	@echo ""
	@echo "══ Platform demo (Docker, seed on boot, Excel baked in) ══"
	@echo "  make demo-package     - regenerate sample Excel for the image"
	@echo "  make demo-build       - Docker image $(DEMO_IMAGE)"
	@echo "  make demo-up          - http://localhost:8000  (+ /examples/sample-plan.xlsx)"
	@echo "  make demo-down        - stop demo containers"
	@echo "  make demo-logs        - follow demo logs"
	@echo "  make demo-deploy-render - redeploy the live Render service"
	@echo "  make demo-deploy-fly  - fly deploy (needs a Fly card on the account)"
	@echo ""

# ── deps ─────────────────────────────────────────────────────────────

install: backend-install frontend-install

backend-install:
	cd $(BACKEND) && python3 -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -e ".[dev]"

frontend-install:
	cd $(FRONTEND) && npm install

# ── run ──────────────────────────────────────────────────────────────

backend-run:
	cd $(BACKEND) && . .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend-run:
	cd $(FRONTEND) && npm run dev

# ── data + Excel ─────────────────────────────────────────────────────

migrate:
	@test -x $(VENV_PY) || $(MAKE) backend-install
	cd $(BACKEND) && . .venv/bin/activate && alembic upgrade head

seed:
	@test -x $(VENV_PY) || $(MAKE) backend-install
	cd $(BACKEND) && . .venv/bin/activate && python -m app.seed
	@echo "Seed plan loaded (~20 tasks)"

excel:
	@test -x $(VENV_PY) || $(MAKE) backend-install
	cd $(BACKEND) && . .venv/bin/activate && python -m app.seed.export_excel --out $(SAMPLE_XLSX)
	@echo "Sample Excel → $(SAMPLE_XLSX)"

# ── frontend artifacts ───────────────────────────────────────────────

frontend-build:
	cd $(FRONTEND) && npm run build

static: frontend-build
	@test -f $(SAMPLE_XLSX) || $(MAKE) excel
	rm -rf $(BACKEND)/static && mkdir -p $(BACKEND)/static/examples
	cp -R $(FRONTEND)/dist/* $(BACKEND)/static/
	cp $(SAMPLE_XLSX) $(BACKEND)/static/examples/sample-plan.xlsx
	@echo "Static UI + sample Excel → $(BACKEND)/static (and /examples/sample-plan.xlsx)"

frontend-lint:
	cd $(FRONTEND) && npm run lint

backend-test:
	@test -x $(VENV_PY) || $(MAKE) backend-install
	cd $(BACKEND) && . .venv/bin/activate && pytest -q

# ── full local build ─────────────────────────────────────────────────

build: install migrate excel static
	@echo ""
	@echo "✓ Full local build ready"
	@echo "  • DB seeded (~20 tasks)"
	@echo "  • Excel:  $(SAMPLE_XLSX)"
	@echo "  • UI:     $(BACKEND)/static  (+ /examples/sample-plan.xlsx)"
	@echo ""
	@echo "Next:  make backend-run   → http://localhost:8000"

build-full: build backend-test frontend-lint
	@echo "✓ build-full OK (tests + lint green)"

check: backend-test frontend-build
	@echo "✓ check OK"

# ── local docker (same as platform demo image) ───────────────────────

docker-up:
	docker compose -f $(ROOT)/docker-compose.yml up --build

docker-down:
	docker compose -f $(ROOT)/docker-compose.yml down

# ── platform demo ────────────────────────────────────────────────────
# Self-contained image: React UI + FastAPI + auto-seed on boot + sample Excel.

demo-package: excel
	@echo "Demo package inputs ready → $(SAMPLE_XLSX)"

demo-build: demo-package
	docker build -f $(ROOT)/Dockerfile -t $(DEMO_IMAGE) $(ROOT)
	@echo "✓ Image: $(DEMO_IMAGE)"

demo-up: demo-package
	docker compose -f $(DEMO_COMPOSE) up -d --build
	@echo ""
	@echo "✓ Platform demo"
	@echo "  App:          http://localhost:8000"
	@echo "  Sample Excel: http://localhost:8000/examples/sample-plan.xlsx"
	@echo "  Health:       http://localhost:8000/health"
	@echo "  API docs:     http://localhost:8000/docs"

demo-down:
	docker compose -f $(DEMO_COMPOSE) down

demo-logs:
	docker compose -f $(DEMO_COMPOSE) logs -f

demo-tunnel:
	@command -v cloudflared >/dev/null || (echo "Install cloudflared: brew install cloudflare/cloudflare/cloudflared"; exit 1)
	cloudflared tunnel --url http://127.0.0.1:8000

demo-deploy-fly: demo-package
	@command -v fly >/dev/null || command -v flyctl >/dev/null || (echo "Install flyctl: https://fly.io/docs/hands-on/install-flyctl/"; exit 1)
	@echo "Deploying to Fly (see fly.toml)…"
	cd $(ROOT) && (command -v fly >/dev/null && fly deploy || flyctl deploy)

demo-deploy-render:
	@echo "Live: https://ai-project-planner-x5da.onrender.com"
	@echo "Dashboard: https://dashboard.render.com/web/srv-dapv2had0e5s73ahbkkg"
	@command -v render >/dev/null && render deploys create srv-dapv2had0e5s73ahbkkg --confirm -o text || true
