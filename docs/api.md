# REST API — AI Project Planner

Base URL: `/api`  
Content-Type: `application/json` (кроме multipart Excel).

Все успешные мутации, изменяющие план, возвращают актуальный `Plan` (или `plan` внутри обёртки), чтобы frontend мог сразу обновить Gantt.

## 1. Conventions

### Plan response shape

```json
{
  "id": "plan-demo",
  "name": "Demo Project",
  "project_start": "2026-10-05",
  "version": 12,
  "updated_at": "2026-09-19T20:00:00Z",
  "tasks": [
    {
      "id": "task-01",
      "name": "Product Discovery",
      "description": "...",
      "assignee": "Maya",
      "duration_days": 3,
      "start_date": "2026-10-05",
      "end_date": "2026-10-07",
      "manual_start": null,
      "predecessor_ids": []
    }
  ]
}
```

### Error shape

```json
{
  "error": {
    "code": "CIRCULAR_DEPENDENCY",
    "message": "Dependency cycle detected: task-18 → task-01 → task-18",
    "details": { "cycle": ["task-18", "task-01", "task-18"] }
  }
}
```

HTTP mapping (ориентир):

| Code | HTTP |
|---|---|
| `INVALID_INPUT` | 422 |
| `TASK_NOT_FOUND` | 404 |
| `CIRCULAR_DEPENDENCY` / `INVALID_DEPENDENCY` / `UNKNOWN_PREDECESSOR` / `INVALID_DURATION` / `DUPLICATE_TASK` / `PLAN_VALIDATION_FAILED` | 400 |
| `VERSION_CONFLICT` | 409 |
| `INTERNAL` | 500 |

### Optimistic concurrency (optional MVP+)

Клиент может слать `If-Match: {version}` или поле `expected_version` в body. При расхождении — `409 VERSION_CONFLICT`.

Для MVP достаточно возвращать новый `version` и last-write-wins при одиночном пользователе.

---

## 2. Health

### `GET /health`

```json
{ "status": "ok" }
```

---

## 3. Plan

### `GET /api/plan`

Текущий активный план (seed или после import).

**Response:** `200 Plan`

### `POST /api/plan/reset` (dev/demo)

Пересоздать seed-план.

**Response:** `200 Plan`

---

## 4. Tasks

### `GET /api/tasks/{task_id}`

**Response:** `200 Task`  
**Errors:** `404 TASK_NOT_FOUND`

### `POST /api/tasks`

Создать задачу.

```json
{
  "name": "QA Pass",
  "description": "Smoke + regression",
  "assignee": "Sam",
  "duration_days": 2,
  "predecessor_ids": ["task-12"]
}
```

**Response:** `201 { "task": Task, "plan": Plan }`

### `PATCH /api/tasks/{task_id}`

Частичное обновление: `name`, `description`, `assignee`, `duration_days`.

```json
{
  "assignee": "Jordan",
  "duration_days": 4
}
```

**Response:** `200 { "task": Task, "plan": Plan }`

### `DELETE /api/tasks/{task_id}`

**Response:** `200 { "plan": Plan }`

### `POST /api/tasks/{task_id}/move`

```json
{ "new_start_date": "2026-11-02" }
```

Семантика: soft pin (`manual_start`), scheduler clamp к earliest FS.

**Response:** `200 { "task": Task, "plan": Plan }`

### `PUT /api/tasks/{task_id}/dependencies`

Полная замена списка предшественников.

```json
{ "predecessor_ids": ["task-03", "task-05"] }
```

**Response:** `200 { "task": Task, "plan": Plan }`  
**Errors:** `400 CIRCULAR_DEPENDENCY`, `400 UNKNOWN_PREDECESSOR`

### `POST /api/tasks/bulk`

Атомарное массовое изменение.

```json
{
  "task_ids": ["task-02", "task-03", "task-04"],
  "changes": {
    "assignee": "Sofia",
    "duration_days": 3
  }
}
```

**Response:** `200 { "plan": Plan, "changes": Change[] }`  
При любой ошибке — rollback всего batch, `400`.

---

## 5. Excel

### `POST /api/excel/import`

`multipart/form-data`, поле файла: `file` (`.xlsx`).

Поведение:

1. Парсинг колонок (RU headers).
2. Построение чернового Plan.
3. Валидация графа + schedule.
4. `replace_plan` в repository.

**Response:** `200 { "plan": Plan, "import_report": { "created": 18, "warnings": [] } }`

Типичные warnings: пустые строки, неизвестный предшественник (строка отброшена/ошибка — политика: **fail closed** на битые зависимости).

### `GET /api/excel/export`

Скачать текущий план как `.xlsx`.

**Response:** `200 application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`  
Header: `Content-Disposition: attachment; filename="plan.xlsx"`

Колонки экспорта совместимы с импортом (+ опционально `id`, `start_date`, `end_date` для удобства; импорт может их игнорировать).

---

## 6. AI Chat

### `POST /api/chat`

```json
{
  "message": "Перенеси UX Wireframes на неделю позже и назначь Maya на все design-задачи",
  "conversation_id": "optional-client-id"
}
```

**Response:** `200`

```json
{
  "conversation_id": "conv-...",
  "message": {
    "role": "assistant",
    "content": "Перенёс UX Wireframes на 2026-10-16 и назначил Maya на 3 design-задачи."
  },
  "plan": { "...": "..." },
  "changes": [
    { "op": "move_task", "task_id": "task-02", "...": "..." }
  ],
  "tool_trace": [
    { "tool": "move_task", "ok": true },
    { "tool": "bulk_update_tasks", "ok": true }
  ]
}
```

`tool_trace` — полезен для demo/debug; можно скрыть флагом в production.

**Поведение при ошибке tool mid-turn:**

- draft transaction откатывается;
- assistant объясняет, что не удалось (с кодом ошибки);
- `plan` = предыдущее валидное состояние.

Conversation history: in-memory per `conversation_id` (MVP) или только last N messages в запросе от клиента.

---

## 7. CORS

Для Vite dev (`localhost:5173`) — разрешённый origin из env.

## 8. Что НЕ входит в MVP API

- Auth / JWT
- WebSocket plan sync
- Pagination задач
- Multi-plan CRUD
- Calendar / working days config
