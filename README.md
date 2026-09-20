# AI Project Planner

AI-native планировщик проектов: интерактивный Gantt, Excel import/export и чат, который массово меняет план через MCP tools.

## Глобальный демо-стенд

| | |
|---|---|
| **Приложение** | https://numerical-minority-binary-beaver.trycloudflare.com |
| **Health** | https://numerical-minority-binary-beaver.trycloudflare.com/health |
| **Sample Excel** | https://numerical-minority-binary-beaver.trycloudflare.com/examples/sample-plan.xlsx |
| **API docs** | https://numerical-minority-binary-beaver.trycloudflare.com/docs |

Публичный стенд = `make demo-up` (Docker: UI + API + seed) + `make demo-tunnel` (Cloudflare Quick Tunnel).  
Пока на машине запущены контейнер и `cloudflared`, ссылка доступна из интернета. После перезапуска туннеля URL меняется — обновите его здесь.

**GitHub:** https://github.com/ikrutov7/ai-project-planner  
**Sample Excel (в репо):** [`examples/sample-plan.xlsx`](examples/sample-plan.xlsx)  
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
```

### Полная локальная сборка (seed + Excel + UI)

```bash
make build
# или с тестами/lint:
make build-full

make backend-run
# → http://localhost:8000
# → http://localhost:8000/examples/sample-plan.xlsx
```

Что делает `make build`: `install` → `migrate` → `excel` (seed ~20 задач + `examples/sample-plan.xlsx`) → `static` (UI в `backend/static`).

Отдельно: `make seed`, `make excel`, `make static`.

### Dev (два процесса, HMR)

```bash
make install
# Terminal 1
make backend-run
# Terminal 2
make frontend-run
# → http://localhost:5173  (Vite proxies /api and /health)
```

### Platform demo (Docker)

Самодостаточный образ: UI + API + auto-seed при старте + sample Excel внутри.

```bash
make demo-up
# → http://localhost:8000
# → http://localhost:8000/examples/sample-plan.xlsx

make demo-logs
make demo-down

# публичный URL с машины:
make demo-up && make demo-tunnel

# площадки:
make demo-deploy-render   # открывает Render Blueprint
make demo-deploy-fly      # нужен: fly auth login
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

### Глобальный демо-стенд (сейчас)

**https://numerical-minority-binary-beaver.trycloudflare.com**

Как поднят:

```bash
make demo-up       # Docker: UI + API + seed + Excel
make demo-tunnel   # публичный Cloudflare URL → localhost:8000
```

Проверка:

```bash
curl -i https://numerical-minority-binary-beaver.trycloudflare.com/health
# → 200 {"status":"ok","database":"ok"}
```

> Quick Tunnel URL одноразовый: при новом `make demo-tunnel` адрес меняется — пропишите новый в этом README (секция «Глобальный демо-стенд»).

### Постоянный хостинг (Render / Fly)

Рекомендуемый путь: один Docker-образ (`Dockerfile`) на **Render**, **Fly.io** или VM. В репо: `render.yaml`, `fly.toml`, `docker-compose.demo.yml`.

```bash
make demo-package          # свежий examples/sample-plan.xlsx
make demo-deploy-render    # Blueprint на Render
# или
make demo-deploy-fly       # fly auth login → fly deploy
```

Локально тот же образ:

```bash
make demo-up
# → http://localhost:8000
# → http://localhost:8000/examples/sample-plan.xlsx
```

#### Render

1. `make demo-deploy-render` или [Deploy Blueprint](https://dashboard.render.com/blueprint/new?repo=https://github.com/ikrutov7/ai-project-planner)
2. Или: New → Web Service → этот репозиторий → Runtime **Docker**, port `8000`
3. Disk (optional): mount `/data` для SQLite
4. Env: `PLANNER_CORS_ORIGINS=*`, опционально `LLM_API_KEY` / `PLANNER_LLM_API_KEY`

#### Fly.io

```bash
make demo-deploy-fly
# эквивалент: fly auth login && fly volumes create planner_data --size 1 -a ai-project-planner-ikrutov && fly deploy
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
