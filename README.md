# AI Project Planner

AI-native планировщик проектов: интерактивный Gantt, Excel import/export и чат, который массово меняет план через MCP tools.

## Демо

Постоянный стенд на Render (без туннеля):

**https://ai-project-planner-x5da.onrender.com**

| | |
|---|---|
| Health | https://ai-project-planner-x5da.onrender.com/health |
| Sample Excel | https://ai-project-planner-x5da.onrender.com/examples/sample-plan.xlsx |
| API docs | https://ai-project-planner-x5da.onrender.com/docs |
| GitHub | https://github.com/ikrutov7/ai-project-planner |
| Dashboard | https://dashboard.render.com/web/srv-dapv2had0e5s73ahbkkg |

На бесплатном плане инстанс засыпает без трафика. Первый запрос после простоя может занять около минуты, затем приложение отвечает как обычно. Seed (~20 задач) поднимается при старте.

**Sample Excel в репо:** [`examples/sample-plan.xlsx`](examples/sample-plan.xlsx)  
**Сценарий:** [`docs/demo.gif`](docs/demo.gif) · [`docs/demo-script.md`](docs/demo-script.md)  
**До продакшена:** [`docs/ROADMAP_TO_PRODUCTION.md`](docs/ROADMAP_TO_PRODUCTION.md)  
**Как использовался AI:** [`docs/AI_ASSISTANTS.md`](docs/AI_ASSISTANTS.md)

## Features

- Seed-план (~20 задач) сразу при открытии
- Gantt с зависимостями Finish-to-Start
- Модалка задачи (описание, даты, исполнитель, predecessors)
- Import / Export Excel (колонки: задача, описание, исполнитель, длительность, предшественники)
- AI chat → MCP tools → мгновенное обновление диаграммы
- Без LLM-ключа работает **demo-агент**; с ключом — OpenAI-compatible function calling

## Architecture

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

1. LLM не пишет в БД и не считает даты как источник истины.
2. Все мутации идут через `PlanService` (scheduler FS + проверка циклов).
3. MCP — typed tool layer над сервисом.

Подробнее: [`docs/architecture.md`](docs/architecture.md), [`docs/mcp-tools.md`](docs/mcp-tools.md), [`docs/api.md`](docs/api.md).

## Stack

| Layer | Tech |
|---|---|
| Frontend | React 19, TypeScript, Vite, TanStack Query |
| Backend | Python 3.11+, FastAPI, Pydantic, SQLAlchemy, SQLite |
| Excel | openpyxl |
| AI | MCP tools + OpenAI-compatible API / demo agent |
| Hosting | Render (Docker, free) |

## Local setup

Нужны Python 3.11+, Node.js 20+, Make. Docker — только для контейнерного демо.

```bash
cp .env.example .env
make build          # install, migrate, seed, Excel, UI
make backend-run    # http://localhost:8000
```

`make build-full` дополнительно гоняет pytest и lint.

Два процесса с HMR: `make backend-run` и `make frontend-run` → http://localhost:5173.

Тот же образ, что на Render, локально:

```bash
make demo-up        # http://localhost:8000
make demo-down
```

## Excel

| задача | описание | исполнитель | длительность | предшественники |
|---|---|---|---|---|
| Product Discovery | … | Maya Chen | 3 | |
| UX Wireframes | … | Maya Chen | 4 | Product Discovery |

Предшественники — имена задач через запятую. Файл: `examples/sample-plan.xlsx` (`make excel` пересобирает его из seed).

## Chat

- `Перенеси UX Wireframes на 7 дней позже`
- `Назначь Maya на design`
- `Создай задачу QA Pass на 2 дня`

С `LLM_API_KEY` / `PLANNER_LLM_API_KEY` агент вызывает те же MCP tools через function calling.

## Deploy

Сервис уже создан на Render из этого репозитория (`render.yaml`, Dockerfile в корне). Push в `main` запускает автодеплой.

Повторно создать сервис:

```bash
render login
render services create --confirm \
  --name ai-project-planner \
  --type web_service \
  --runtime docker \
  --repo https://github.com/ikrutov7/ai-project-planner \
  --branch main \
  --plan free \
  --region frankfurt \
  --num-instances 1 \
  --health-check-path /health \
  --env-var 'PLANNER_CORS_ORIGINS=*' \
  --env-var PLANNER_SERVE_FRONTEND=true \
  --env-var PLANNER_AGENT_DEMO_MODE=true \
  --env-var 'PLANNER_DATABASE_URL=sqlite:////tmp/planner.db'
```

Fly.io (`fly.toml`, `make demo-deploy-fly`) — запасной вариант; аккаунту нужна платёжная карта.

## Repository layout

```text
frontend/   React app
backend/    FastAPI + domain + MCP + agent
docs/       Architecture, roadmap, AI notes, demo
examples/   sample-plan.xlsx
Dockerfile  production image (UI + sample Excel)
```

## License

MIT (учебный / assignment MVP).
