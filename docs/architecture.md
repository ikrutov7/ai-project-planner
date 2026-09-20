# Architecture — AI-Native Project Planner (MVP)

## 1. Цель продукта

AI-native планировщик проектов с интерактивной диаграммой Гантта.

Пользователь сразу видит seed-план, может импортировать/экспортировать Excel и изменять план естественным языком через AI chat. Все мутации мгновенно отражаются на Gantt.

## 2. Принципы MVP

1. **Один процесс backend** — FastAPI + domain + MCP + LLM orchestration в одном сервисе.
2. **Один источник истины** — `Plan` в domain layer; UI, Excel и AI не пишут в БД напрямую.
3. **Детерминизм планирования** — даты считает scheduler (Finish-to-Start), не LLM.
4. **LLM = intent → tools**, не «источник правды».
5. **Простая persistence** — SQLite сейчас; repository interface готов к PostgreSQL.
6. **Без лишнего** — нет Redis, Kafka, Kubernetes, микросервисов, WebSocket-брокеров.

## 3. Высокоуровневая архитектура

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (React + TypeScript)                              │
│  ┌──────────────┐  ┌─────────────┐  ┌────────────────────┐  │
│  │ Gantt Chart  │  │ Task Modal  │  │ AI Chat Panel      │  │
│  └──────┬───────┘  └──────┬──────┘  └─────────┬──────────┘  │
│         │                 │                    │             │
│         └────────────┬────┴────────────────────┘             │
│                      │  REST (JSON) + file upload/download   │
└──────────────────────┼───────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Backend (Python + FastAPI)                                 │
│                                                             │
│  API routes ──► PlanService ◄── MCP tools ◄── Agent loop    │
│                      │              ▲              │        │
│                      │              │         LLM API       │
│                      ▼              │                       │
│                 Repository ──► SQLite                       │
│                                                             │
│  Excel import/export ◄── PlanService                        │
└─────────────────────────────────────────────────────────────┘
```

### Потоки данных

| Источник | Путь | Результат |
|---|---|---|
| UI (клик / modal) | REST → PlanService → repository | обновлённый Plan DTO |
| Excel import | REST multipart → Excel parser → PlanService.replace_plan | новый Plan |
| Excel export | REST → Excel builder ← PlanService.get_plan | `.xlsx` файл |
| AI chat | REST `/chat` → Agent → MCP tools → PlanService | Plan + assistant message |

## 4. Frontend architecture

### Стек

- React 18+ + TypeScript
- Vite
- TanStack Query (серверный state плана)
- Легкий UI state (React context / Zustand) только для chat UI и modal
- Gantt: библиотека с кастомной обёрткой (например `@wamra/gantt-task-react` или аналог) — конкретный выбор на этапе реализации UI
- Стили: CSS Modules или один лёгкий CSS-файл с CSS variables (без тяжёлого UI kit)

### Структура UI

```
┌──────────────────────────────────────────────┐
│ Header: title | Import Excel | Export Excel  │
├────────────────────────────┬─────────────────┤
│                            │                 │
│     Gantt Chart            │   AI Chat       │
│     (main plane)           │   (right ~360)  │
│                            │                 │
└────────────────────────────┴─────────────────┘
         │
         └─ click task → Task Detail Modal
```

### Слои frontend

1. **`api/`** — typed fetch clients (`getPlan`, `importExcel`, `exportExcel`, `sendChat`, CRUD tasks).
2. **`domain/`** — TypeScript DTO, зеркалящие backend Plan/Task (без бизнес-логики scheduler).
3. **`features/gantt/`** — адаптер Plan → Gantt rows/bars, handlers move/resize (через REST).
4. **`features/chat/`** — messages list, input, streaming optional (MVP: request/response).
5. **`features/task-modal/`** — detail view + edit form.
6. **Import/Export Excel** — кнопки в `AppShell` (multipart + download blob).

### State strategy

- **Plan** — единственный server state, ключ `['plan']` в React Query.
- После любого успешного mutation (UI / chat / import) — `invalidateQueries(['plan'])` или использовать `plan` из response.
- Chat history — локальный UI state (не обязательно persist в MVP).
- Optimistic updates — **не обязательны** в MVP; достаточно мгновенного refetch после ответа.

## 5. Backend architecture

### Слои (сверху вниз)

```
api/          HTTP adapters (FastAPI routers)
agent/        LLM orchestration (chat turn → tool calls)
mcp/          MCP tool registry + in-process server
excel/        xlsx parse/serialize
plan/         domain: models, scheduler, validation, PlanService
storage/      repository implementations (SQLite, memory for tests)
```

### Ключевые компоненты

| Компонент | Ответственность |
|---|---|
| `PlanService` | Единственный gateway мутаций; draft transactions для AI |
| `scheduler` | Детерминический FS schedule; cycle helpers |
| `validation` | Инварианты плана |
| `PlanRepository` | Persistence abstraction |
| `MCPServer` | Typed tools над PlanService |
| `AgentService` | LLM loop: messages → tool_calls → MCP → final reply |
| Excel services | Mapping rows ↔ Task graph |

### Почему in-process MCP

Для MVP MCP server живёт **в том же процессе**, что и FastAPI:

- Agent вызывает `MCPServer.call_tool(name, args)` напрямую.
- Опционально: `python -m app.mcp.server` для stdio MCP clients (отладка в Cursor и т.п.).
- Нет отдельного MCP microservice.

## 6. Persistence

### MVP: SQLite

- Один файл `data/planner.db` (или путь из env `DATABASE_URL`).
- Таблицы: `plans`, `tasks` (или JSON blob плана — см. trade-offs).
- Рекомендация MVP: **одна строка Plan как JSON document** + `version` / `updated_at` для простоты атомарности.
  - Альтернатива (нормализованная): `plans` + `tasks` + `dependencies` — лучше для SQL-отчётов, сложнее для атомарных AI-транзакций.

**Выбор MVP:** document-style JSON plan в SQLite + optimistic `version` check.

### Repository interface

```text
PlanRepository
  get_active_plan() -> Plan
  save_plan(plan: Plan) -> Plan   # version bump / optimistic lock
  replace_plan(plan: Plan) -> Plan  # Excel import / reset seed
```

Реализации:

- `SqlitePlanRepository`
- `MemoryPlanRepository` (тесты, ephemeral)
- (будущее) `PostgresPlanRepository` — тот же interface, другой driver

`PlanService` зависит только от Protocol/`PlanStore`, не от SQLite.

## 7. Структура директорий

```text
/
├── docs/
│   ├── architecture.md
│   ├── data-model.md
│   ├── api.md
│   ├── mcp-tools.md
│   ├── AI_ASSISTANTS.md
│   └── ROADMAP_TO_PRODUCTION.md
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── api/
│   │   │   ├── routes_plan.py
│   │   │   ├── routes_tasks.py
│   │   │   ├── routes_excel.py
│   │   │   ├── routes_chat.py
│   │   │   └── schemas.py
│   │   ├── plan/
│   │   │   ├── models.py
│   │   │   ├── errors.py
│   │   │   ├── scheduler.py
│   │   │   ├── validation.py
│   │   │   └── service.py
│   │   ├── storage/
│   │   │   ├── protocol.py
│   │   │   ├── memory.py
│   │   │   ├── sqlite.py
│   │   │   └── seed.py
│   │   ├── excel/
│   │   │   ├── schema.py
│   │   │   ├── import_xlsx.py
│   │   │   ├── export_xlsx.py
│   │   │   └── service.py
│   │   ├── mcp/
│   │   │   ├── tools.py
│   │   │   └── server.py
│   │   └── agent/
│   │       ├── service.py
│   │       ├── prompts.py
│   │       ├── llm_client.py
│   │       └── fake_llm.py
│   └── tests/
│       ├── test_domain_*.py
│       ├── test_api_*.py
│       ├── test_excel_*.py
│       ├── test_mcp_*.py
│       └── test_agent_*.py
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       ├── domain/
│       ├── features/
│       │   ├── gantt/
│       │   ├── chat/
│       │   ├── task-modal/
│       │   └── excel/
│       └── styles/
├── examples/
│   └── sample-plan.xlsx
├── docker-compose.yml          # optional: api + static
├── Dockerfile                  # optional multi-stage
└── README.md
```

## 8. AI / MCP interaction (кратко)

Подробности — в `docs/mcp-tools.md`.

1. Пользователь пишет в chat.
2. Backend загружает текущий plan summary в system/context.
3. LLM возвращает tool calls (function calling).
4. Agent исполняет tools через MCP → PlanService (внутри draft transaction на весь turn).
5. Результаты tools возвращаются в LLM.
6. Финальный ответ + актуальный Plan уходят на frontend.
7. Frontend обновляет Gantt.

## 9. Real-time updates после AI

**MVP: synchronous response body.**

```json
{
  "message": { "role": "assistant", "content": "..." },
  "plan": { "...full plan..." },
  "changes": [ ... ]
}
```

Frontend применяет `plan` из ответа → Gantt обновляется без polling/WebSocket.

Опционально позже: SSE для streaming текста; plan всё равно отдаётся в конце turn.

## 10. Deployment (MVP)

См. `Makefile` (`demo-up` / `demo-deploy-*`) и корневой `Dockerfile`.

- Backend: `uvicorn app.main:app`
- Frontend: static build, раздаётся nginx или FastAPI `StaticFiles`
- SQLite volume mount
- Env: `LLM_API_KEY`, `LLM_BASE_URL`, `DATABASE_URL`, `CORS_ORIGINS`
- Docker Compose: один сервис `app` (+ volume для db и uploads temp)

## 11. Non-goals (MVP)

- Multi-user auth / multi-tenant
- Conflict-free collaborative editing
- Resource leveling / calendars / weekends
- Dependency types besides FS
- Undo stack UI (можно хранить `recent_changes`, но без UI undo)
- Streaming tool execution UI

## 12. Связанные документы

- [data-model.md](./data-model.md)
- [api.md](./api.md)
- [mcp-tools.md](./mcp-tools.md)
- [ROADMAP_TO_PRODUCTION.md](./ROADMAP_TO_PRODUCTION.md)
- [AI_ASSISTANTS.md](./AI_ASSISTANTS.md)

## 13. Архитектурные решения и trade-offs

| # | Решение | Альтернатива | Почему так в MVP | Цена |
|---|---|---|---|---|
| 1 | Монолит: FastAPI + domain + MCP + agent | Отдельный MCP/AI service | Проще deploy, отладка, атомарные транзакции | Вертикальное масштабирование позже |
| 2 | In-process MCP | Только внешний stdio MCP | Низкая latency, единый PlanService | Меньше «чистой» изоляции процесса |
| 3 | LLM → tools → PlanService; даты считает scheduler | LLM сам выставляет даты | Детерминизм, нет «плывущего» плана | Нужен хороший tool UX для move |
| 4 | Assignee = string на Task | Таблица assignees | Excel/NL free-form | Нет справочника ролей/нагрузки |
| 5 | Dependencies как `predecessor_ids` | Отдельная таблица edges | Проще JSON plan + валидация | Сложнее SQL-аналитика графа |
| 6 | Только FS, lag=0 | SS/FF/FS+lag, календари | Достаточно для демо Гантта | Не Microsoft Project |
| 7 | Inclusive duration | Exclusive end | Понятно для «3 дня = пн–ср» | Нужна дисциплина в тестах |
| 8 | Soft pin `manual_start` | Жёсткий start или только constraints | Move не ломается при reschedule | Семантика «не раньше preds» |
| 9 | Draft transaction на AI turn | Commit на каждый tool | Атомарность NL-запроса | Длинный turn держит draft |
| 10 | SQLite JSON document plan | Нормализованные таблицы / сразу Postgres | Атомарный replace + лёгкий миграционный путь | Слабее ad-hoc SQL queries |
| 11 | Repository Protocol | Прямой SQL в service | Смена SQLite→Postgres без переписывания domain | Тонкий слой абстракции |
| 12 | Sync chat response с полным `plan` | WebSocket / SSE plan stream | «Мгновенно» без infra | Нет live multi-tab sync |
| 13 | React Query как plan cache | Global event bus | Простой invalidate/setQueryData | Optimistic UI позже |
| 14 | FakeLLM для agent tests | Только recorded HTTP | CI без ключей и flaky сети | Скрипты нужно поддерживать |
| 15 | Один active plan | Multi-project | Соответствует тестовому сценарию | Нет портфеля проектов |
| 16 | Fail-closed Excel deps | Import с warnings и дропом рёбер | Не получить битый граф | Строже к качеству файла |
| 17 | Bulk tool + REST bulk | Только N single calls | Массовые NL-операции и атомарность | Ещё один контракт |
| 18 | Static frontend из FastAPI/Docker | CDN + отдельно API | Один контейнер для сдачи | Чуть менее гибкий scaling |

### Сознательно отложено

- Auth, multi-tenancy, CRDT/collaboration  
- Redis/Kafka/очереди  
- Kubernetes / service mesh  
- Working calendars, resource leveling  
- Полный undo/redo UI  
