# Implementation Plan — Cursor-sized stages

Каждый этап рассчитан на **один** сфокусированный Cursor prompt.  
Порядок строгий: следующий этап опирается на предыдущий.  
**Этот документ — план; реализация начинается только после явного запроса.**

Уже существующий domain/MCP/Excel-код в репозитории учитывать как заготовку: этап либо «довести/зафиксировать», либо «добавить недостающее». Не переписывать без причины.

---

## Stage 0 — Docs freeze & repo baseline

**Цель:** зафиксировать контракты и скелет монорепо.

**Сделать:**

- Убедиться, что `docs/*` актуальны.
- `README.md`: цель MVP, стек, как запускать позже.
- Папки `backend/`, `frontend/`, `examples/` существуют.
- `.gitignore`: `.venv`, `node_modules`, `*.db`, `.env`, dist.

**Готово когда:** документы согласованы; нет требования писать фичи.

**Cursor prompt (пример):**  
«Обнови README под архитектуру из docs/; добавь .gitignore; ничего не реализуй в app logic.»

---

## Stage 1 — Domain models & errors (если нужно довести)

**Цель:** канонические `Plan`, `Task`, `Dependency`, `Change`, error codes.

**Сделать:**

- Модели + validators (`duration_days`, unique preds, name).
- Structured domain errors.

**Тесты:** создание моделей, rejection invalid fields.

**Готово когда:** `pytest` на models/errors зелёный.

---

## Stage 2 — Scheduler & cycle detection

**Цель:** детерминический FS scheduler + cycle helpers.

**Сделать:**

- Inclusive end dates.
- Topo schedule от `project_start`.
- `would_create_cycle`, validate FS consistency.
- Soft pin `manual_start`.

**Тесты:** chain, diamond, cycle 2-node/long, pin clamp.

**Готово когда:** scheduler tests зелёные.

---

## Stage 3 — PlanService + draft transactions

**Цель:** единый mutation gateway.

**Сделать:**

- CRUD-ish ops: create/update/delete/move/set deps/assignee/duration.
- `begin_draft` / `commit` / `rollback` / `transaction()`.
- `_finalize`: schedule → assert_valid → save.

**Тесты:** успешные мутации; rollback изоляция; delete cleans dependents.

**Готово когда:** все мутации только через PlanService.

---

## Stage 4 — Seed data + memory repository

**Цель:** демо-план ~18 задач; `MemoryPlanRepository`.

**Сделать:**

- `build_seed_plan()` со стабильными id.
- Store get/save.
- App bootstrap: empty → seed.

**Тесты:** seed валиден и scheduleable.

---

## Stage 5 — SQLite repository behind Protocol

**Цель:** persistence без смены PlanService API.

**Сделать:**

- `PlanRepository` protocol.
- `SqlitePlanRepository` (JSON payload + version).
- Config `DATABASE_URL` / path.
- Миграция: create table if not exists.

**Тесты:** save/load roundtrip; version bump; memory vs sqlite одинаковый service behavior.

**Готово когда:** можно переключить store через DI.

---

## Stage 6 — Excel import

**Цель:** `.xlsx` → Plan.

**Сделать:**

- Колонки: задача, описание, исполнитель, длительность, предшественники.
- Two-pass link by name/id.
- Fail closed на циклы / unknown preds.
- `PlanService.replace_plan` / import API method.

**Артефакт:** `examples/sample-plan.xlsx`.

**Тесты:** happy path; missing column; cycle file; empty sheet.

---

## Stage 7 — Excel export

**Цель:** Plan → `.xlsx` совместимый с import.

**Сделать:**

- Export columns (+ optional id/dates).
- Roundtrip test: export(seed) → import ≈ same graph.

**Тесты:** roundtrip; Content-Type на API (stage 8).

---

## Stage 8 — FastAPI: plan & tasks REST

**Цель:** HTTP API для UI без AI.

**Сделать:**

- `GET /api/plan`, task CRUD, move, dependencies, bulk.
- Pydantic response schemas (tasks as array).
- Error → JSON error envelope.
- CORS для Vite.
- `GET /health`.

**Тесты:** `httpx`/`TestClient` для каждого endpoint.

---

## Stage 9 — FastAPI: Excel routes

**Цель:** import/export HTTP.

**Сделать:**

- `POST /api/excel/import` multipart.
- `GET /api/excel/export` file response.
- Wiring к Excel services + PlanService.

**Тесты:** upload sample; download bytes openable by openpyxl.

---

## Stage 10 — MCP tool layer

**Цель:** typed tools над PlanService.

**Сделать:**

- Input schemas + handlers для полного списка tools.
- `MCPServer.call_tool` + structured errors.
- Optional stdio entrypoint.

**Тесты:** каждый tool; cycle; bulk rollback; **без LLM**.

---

## Stage 11 — LLM client abstraction + FakeLLM

**Цель:** провайдер-независимый chat + test double.

**Сделать:**

- `LLMClient` protocol.
- OpenAI-compatible HTTP client (env-based).
- `FakeLLM` / scripted responses.
- System prompt + tool schema export from MCP.

**Тесты:** FakeLLM script drives N tool calls; unknown tool rejected.

---

## Stage 12 — AgentService + `/api/chat`

**Цель:** NL → tools → updated plan.

**Сделать:**

- Agent loop с max iterations.
- One draft transaction per turn.
- Response: message + plan + changes (+ tool_trace).
- Graceful failure messaging.

**Тесты:** scripted multi-tool turn; mid-turn error → rollback; plan in response matches store.

---

## Stage 13 — Frontend scaffold

**Цель:** Vite + React + TS приложение.

**Сделать:**

- Layout: Gantt area + right chat + header actions.
- API client + Plan types.
- React Query `GET /api/plan` on load.
- Empty/error states.

**Готово когда:** при открытии видны seed tasks (хотя бы списком, если Gantt ещё stub).

---

## Stage 14 — Gantt chart integration

**Цель:** интерактивная диаграмма.

**Сделать:**

- Map Plan → Gantt tasks.
- Display bars, deps if library supports.
- Click → open modal hook.
- Optional: drag move → `POST .../move` → refetch plan.

**Готово когда:** seed виден как Gantt; даты соответствуют API.

---

## Stage 15 — Task detail modal + manual edits

**Цель:** просмотр/правка задачи с UI.

**Сделать:**

- Modal: fields + save via PATCH.
- Delete confirm.
- Deps editor (simple multi-select / id list).

**Готово когда:** UI mutations отражаются на Gantt.

---

## Stage 16 — Excel UI import/export

**Цель:** кнопки в header.

**Сделать:**

- File input → import → invalidate plan.
- Export download via blob.
- Toast/error on bad file.

---

## Stage 17 — AI Chat UI

**Цель:** правая панель чата.

**Сделать:**

- Message list + input.
- `POST /api/chat` → append assistant message.
- Apply `plan` from response to Query cache (Gantt updates instantly).
- Show simple error if agent fails.

**Готово когда:** NL «перенеси задачу X» меняет Gantt без reload страницы.

---

## Stage 18 — E2E happy path (lightweight)

**Цель:** сквозной сценарий.

**Сделать:**

- Backend integration script или Playwright smoke:
  1. open app → seed Gantt
  2. import excel
  3. chat mutation
  4. export excel
- Document manual demo script in README.

---

## Stage 19 — Deployment packaging

**Цель:** простой deploy.

**Сделать:**

- `Dockerfile` multi-stage: build frontend, copy into backend static, run uvicorn.
- `docker-compose.yml`: app + volume `./data`.
- `.env.example`: LLM_*, DATABASE_URL, CORS.
- Healthcheck.
- README: run locally (dev) и через Docker.

**Не делать:** K8s, Redis, managed DB (опционально Postgres URL later).

---

## Stage 20 — Hardening pass

**Цель:** полировка MVP перед сдачей.

**Сделать:**

- Логирование request_id на chat turns.
- Ограничение размера Excel.
- Убрать debug tool_trace или за флаг.
- Проверка CORS/production static paths.
- Краткий `docs/demo-script.md` (опционально).

---

## Mapping: requirements → stages

| Требование | Stages |
|---|---|
| Frontend/backend architecture | 0, 8, 13 |
| Directory structure | 0 |
| Data model | 1, docs |
| REST API | 8–9, 12 |
| MCP architecture & tools | 10 |
| LLM ↔ MCP | 11–12 |
| Validate AI actions | 3, 10, 12 |
| Cycle prevention | 2, 10 |
| Bulk ops | 3, 8, 10 |
| Frontend updates after AI | 12, 17 |
| Excel import/export | 6–7, 9, 16 |
| Seed data | 4 |
| Backend tests | 1–9 continuously |
| MCP tests | 10 |
| Agent without real LLM | 11–12 |
| Deployment | 19 |

---

## Suggested Cursor prompt template

```text
Implement ONLY Stage N from docs/implementation-plan.md.
Follow docs/architecture.md, data-model.md, api.md, mcp-tools.md.
Do not start later stages.
Add/adjust tests described in the stage.
Keep the architecture simple (SQLite/memory, no Redis/Kafka).
```
