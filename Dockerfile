# Multi-stage: React UI + FastAPI, sample Excel baked in, seed on first boot.
FROM node:20-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLANNER_DATABASE_URL=sqlite:////data/planner.db \
    PLANNER_SERVE_FRONTEND=true \
    PLANNER_CORS_ORIGINS=* \
    PLANNER_AGENT_DEMO_MODE=true

RUN apt-get update && apt-get install -y --no-install-recommends curl \
  && rm -rf /var/lib/apt/lists/* \
  && mkdir -p /data

COPY backend/pyproject.toml ./
COPY backend/app ./app
COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY --from=frontend-build /frontend/dist ./static

# Sample Excel for reviewers (also available via Export in UI)
RUN mkdir -p ./static/examples
COPY examples/sample-plan.xlsx ./static/examples/sample-plan.xlsx

RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir -e .

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
