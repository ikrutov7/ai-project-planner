# AI Project Planner

AI-native планировщик проектов: интерактивный Gantt, Excel import/export и чат, который массово меняет план через MCP tools.

**Live demo:** см. раздел [Deploy](#deploy) ниже (после публикации).  
**Sample Excel:** [`examples/sample-plan.xlsx`](examples/sample-plan.xlsx)  
**Demo walkthrough:** [`docs/demo.gif`](docs/demo.gif) · [`docs/demo-script.md`](docs/demo-script.md)  
**Production backlog:** [`docs/ROADMAP_TO_PRODUCTION.md`](docs/ROADMAP_TO_PRODUCTION.md)  
**AI usage:** [`docs/AI_ASSISTANTS.md`](docs/AI_ASSISTANTS.md)

## Features

- Seed-план (~20 задач) сразу при открытии
- Gantt с зависимостями Finish-to-Start
- Модалка задачи (описание, даты, исполнитель, predecessors)
- Import / Export Excel (колонки: задача, описание, исполнитель, длительность, предшественники)
- AI chat → MCP tools → мгновенное обновление диаграммы
- Без LLM-ключа работает **demo-агент**; с ключом — OpenAI-compatible function calling

## Architecture (коротко)

```text
React (Gantt + Chat + Modal)
        │ REST / multipart
        ▼
FastAPI ── PlanService ── SQLite
              ▲
         MCP tools
              ▲
         Agent (LLM or demo)
```

Принципы:

1. LLM не пишет в БД и не считает даты как источник истины.
2. Все мутации идут через `PlanService` (+ scheduler FS + cycle checks).
3. MCP — typed tool layer над сервисом (in-process; stdio entrypoint опционален).

Подробнее: [`docs/architecture.md`](docs/architecture.md), [`docs/mcp-tools.md`](docs/mcp-tools.md), [`docs/api.md`](docs/api.md).

## Stack

| Layer | Tech |
|---|---|
| Frontend | React 19, TypeScript, Vite, TanStack Query |
| Backend | Python 3.11+, FastAPI, Pydantic, SQLAlchemy, SQLite |
| Excel | openpyxl |
| AI | MCP tools + OpenAI-compatible API / demo agent |

## Prerequisites

- Python 3.11+
- Node.js 20+
- Make (optional)
- Docker (optional, для единого контейнера)

## Local setup

```bash
cp .env.example .env
make install
```

### Dev (два процесса)

```bash
# Terminal 1
make backend-run
# → http://localhost:8000/health
# → http://localhost:8000/docs

# Terminal 2
make frontend-run
# → http://localhost:5173  (Vite proxies /api and /health)
```

### Single container (UI + API)

```bash
docker compose up --build
# → http://localhost:8000
```

### Seed / tests

```bash
make seed
make backend-test
make frontend-build
```

## Excel format

| задача | описание | исполнитель | длительность | предшественники |
|---|---|---|---|---|
| Product Discovery | … | Maya Chen | 3 | |
| UX Wireframes | … | Maya Chen | 4 | Product Discovery |

Предшественники — имена задач через запятую. Пример: `examples/sample-plan.xlsx`.

## Chat examples (demo agent)

- `Перенеси UX Wireframes на 7 дней позже`
- `Назначь Maya на design`
- `Создай задачу QA Pass на 2 дня`

С `LLM_API_KEY` / `PLANNER_LLM_API_KEY` агент использует tool-calling поверх тех же MCP tools.

## Deploy

Рекомендуемый путь: один Docker-образ (этот репозиторий, `Dockerfile` в корне) на **Render**, **Fly.io** или VM.

### Render (Web Service)

1. New → Web Service → подключить репозиторий
2. Runtime: Docker
3. Dockerfile path: `./Dockerfile`
4. Port: `8000`
5. Disk (optional): mount `/data` для SQLite
6. Env: `PLANNER_CORS_ORIGINS=*`, опционально `LLM_API_KEY`

### Fly.io

```bash
fly launch --dockerfile Dockerfile
fly volumes create planner_data --size 1
# привязать volume к /data в fly.toml
fly deploy
```

## Repository layout

```text
frontend/   React app
backend/    FastAPI + domain + MCP + agent
docs/       Architecture, roadmap, AI notes, demo
examples/   sample-plan.xlsx
Dockerfile  production image (UI embedded)
```

## License

MIT (учебный / assignment MVP).
