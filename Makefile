# AI Project Planner — local build + platform demo
# Requires: Python 3.11+, Node 20+ (nvm recommended), Docker (for demo-*)

.PHONY: help install backend-install frontend-install \
	backend-run frontend-run backend-test frontend-build frontend-lint \
	migrate seed excel static \
	build build-full check \
	docker-up docker-down \
	demo-build demo-up demo-down demo-logs demo-tunnel demo-deploy-fly demo-package

ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
BACKEND := $(ROOT)/backend
FRONTEND := $(ROOT)/frontend
EXAMPLES := $(ROOT)/examples
SAMPLE_XLSX := $(EXAMPLES)/sample-plan.xlsx
DEMO_IMAGE := ai-project-planner:demo
VENV := $(BACKEND)/.venv/bin/activate

help:
	@echo ""
	@echo "Local development"
	@echo "  make install          - backend + frontend deps"
	@echo "  make backend-run      - FastAPI :8000 (reload)"
	@echo "  make frontend-run     - Vite :5173"
	@echo "  make seed             - force-load demo plan (~20 tasks)"
	@echo "  make excel            - seed + write examples/sample-plan.xlsx"
	@echo "  make static           - build UI into backend/static"
	@echo "  make build            - install + migrate + seed + excel + static"
	@echo "  make build-full       - build + pytest + frontend lint"
	@echo "  make check            - backend tests + frontend build"
	@echo ""
	@echo "Platform demo (Docker image with UI + seed + sample Excel)"
	@echo "  make demo-build       - build Docker image $(DEMO_IMAGE)"
	@echo "  make demo-up          - run demo on http://localhost:8000"
	@echo "  make demo-down        - stop demo compose"
	@echo "  make demo-logs        - follow demo logs"
	@echo "  make demo-tunnel      - Cloudflare quick tunnel to :8000"
	@echo "  make demo-package     - build image + write sample Excel (CI/demo prep)"
	@echo "  make demo-deploy-fly  - fly deploy (needs fly auth login)"
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
	cd $(BACKEND) && . .venv/bin/activate && alembic upgrade head

seed:
	cd $(BACKEND) && . .venv/bin/activate && python -m app.seed

excel: seed
	cd $(BACKEND) && . .venv/bin/activate && python -m app.seed.export_excel --out $(SAMPLE_XLSX)
	@echo "Sample Excel → $(SAMPLE_XLSX)"

# ── frontend artifacts ───────────────────────────────────────────────

frontend-build:
	cd $(FRONTEND) && npm run build

static: frontend-build
	rm -rf $(BACKEND)/static && mkdir -p $(BACKEND)/static
	cp -R $(FRONTEND)/dist/* $(BACKEND)/static/
	mkdir -p $(BACKEND)/static/examples
	@test -f $(SAMPLE_XLSX) || $(MAKE) excel
	cp $(SAMPLE_XLSX) $(BACKEND)/static/examples/sample-plan.xlsx
	@echo "Static UI + sample Excel → $(BACKEND)/static"

frontend-lint:
	cd $(FRONTEND) && npm run lint

backend-test:
	cd $(BACKEND) && . .venv/bin/activate && pytest -q

# ── full local build ─────────────────────────────────────────────────

build: install migrate excel static
	@echo ""
	@echo "Full local build ready:"
	@echo "  • DB seeded (~20 tasks)"
	@echo "  • $(SAMPLE_XLSX)"
	@echo "  • UI in backend/static (incl. /examples/sample-plan.xlsx)"
	@echo "Run: make backend-run  → http://localhost:8000"

build-full: build backend-test frontend-lint
	@echo "build-full OK (tests + lint green)"

check: backend-test frontend-build
	@echo "check OK"

# ── local docker (compose) ───────────────────────────────────────────

docker-up:
	docker compose -f $(ROOT)/docker-compose.yml up --build

docker-down:
	docker compose -f $(ROOT)/docker-compose.yml down

# ── platform demo ────────────────────────────────────────────────────
# Self-contained image: React UI + FastAPI + auto-seed + sample Excel baked in.

demo-package: excel
	@echo "Demo package inputs ready (seed Excel at $(SAMPLE_XLSX))"

demo-build: demo-package
	docker build -f $(ROOT)/Dockerfile -t $(DEMO_IMAGE) $(ROOT)
	@echo "Image: $(DEMO_IMAGE)"

demo-up: demo-build
	docker compose -f $(ROOT)/docker-compose.demo.yml up -d --build
	@echo "Demo → http://localhost:8000"
	@echo "Sample Excel → http://localhost:8000/examples/sample-plan.xlsx"

demo-down:
	docker compose -f $(ROOT)/docker-compose.demo.yml down

demo-logs:
	docker compose -f $(ROOT)/docker-compose.demo.yml logs -f

demo-tunnel:
	@command -v cloudflared >/dev/null || (echo "Install cloudflared first"; exit 1)
	cloudflared tunnel --url http://127.0.0.1:8000

demo-deploy-fly: demo-package
	@command -v fly >/dev/null || command -v flyctl >/dev/null || (echo "Install flyctl: https://fly.io/docs/hands-on/install-flyctl/"; exit 1)
	@echo "Deploying to Fly (app from fly.toml)…"
	cd $(ROOT) && (fly deploy || flyctl deploy)

# Legacy aliases
docker-up: demo-up
