# MCP Tools & AI Agent Architecture

## 1. Роль MCP в системе

MCP (Model Context Protocol) — **контрактный слой tools** между LLM и domain.

```
User message
    → AgentService (LLM loop)
        → MCPServer.call_tool(name, arguments)
            → PlanService mutation
                → schedule + validate
                    → Repository
```

Правила:

1. LLM **никогда** не пишет в SQLite и не считает даты вручную как источник истины.
2. MCP tools — тонкие typed adapters над `PlanService`.
3. Tools не содержат LLM-логики; тестируются без LLM.
4. В MVP MCP server **in-process** (тот же Python process, что FastAPI).

## 2. MCP architecture

### Компоненты

| Файл | Назначение |
|---|---|
| `app/mcp/tools.py` | Pydantic input schemas + handler registry |
| `app/mcp/server.py` | `list_tools`, `call_tool`, optional stdio JSON-RPC |

### Два режима запуска

1. **In-process** (основной): `MCPServer(plan_service).call_tool(...)` из AgentService.
2. **Stdio** (опционально): `python -m app.mcp.server` — для внешнего MCP client / отладки.

### Tool result envelope

Успех:

```json
{
  "success": true,
  "data": { "...tool-specific..." },
  "plan_version": 14
}
```

Ошибка:

```json
{
  "success": false,
  "error": {
    "code": "CIRCULAR_DEPENDENCY",
    "message": "...",
    "details": {}
  }
}
```

Для read-tools `data` содержит snapshot; для write-tools — краткий diff + достаточно контекста, чтобы LLM продолжил (часто `task` + summary). Полный plan Agent может подтянуть через `get_plan` или держать в памяти turn'а.

## 3. Список MCP tools

| Tool | Тип | Описание | Input |
|---|---|---|---|
| `get_plan` | read | Полный snapshot плана | `{}` |
| `get_task` | read | Одна задача | `{ task_id }` |
| `search_tasks` | read | Поиск по name/description/assignee | `{ query }` |
| `create_task` | write | Создать задачу | `{ name, description?, assignee?, duration_days, predecessor_ids? }` |
| `update_task` | write | Имя/описание | `{ task_id, name?, description? }` |
| `delete_task` | write | Удалить (+ вычистить из dependents) | `{ task_id }` |
| `move_task` | write | Soft-pin start date | `{ task_id, new_start_date: YYYY-MM-DD }` |
| `set_dependencies` | write | Заменить predecessors (cycle-safe) | `{ task_id, predecessor_ids: string[] }` |
| `set_assignee` | write | Назначить/снять исполнителя | `{ task_id, assignee: string \| null }` |
| `set_duration` | write | Изменить длительность | `{ task_id, duration_days }` |
| `bulk_update_tasks` | write | Массовые изменения атомарно | `{ task_ids, changes: { assignee?, duration_days?, description? } }` |

### Почему такой набор

Покрывает пользовательский сценарий:

- перенос → `move_task`
- зависимости → `set_dependencies`
- добавить/удалить → `create_task` / `delete_task`
- исполнители → `set_assignee` / `bulk_update_tasks`
- массовые правки → `bulk_update_tasks`

Read tools нужны, чтобы LLM не галлюцинировал id и состояние.

## 4. Как LLM взаимодействует с MCP

### Agent loop (MVP)

```
1. Build messages:
   - system prompt (правила + семантика дат/зависимостей)
   - compact plan summary (id, name, dates, preds, assignee)
   - conversation history (last N)
   - user message

2. Call LLM with tool schemas (function calling / tools API)

3. While response has tool_calls (max K iterations, e.g. 8):
   a. For each tool_call → MCPServer.call_tool
   b. Append tool results to messages
   c. Call LLM again

4. Commit draft transaction (if any pending) OR already committed per-tool

5. Return assistant text + final plan + changes
```

### Transaction strategy (рекомендация)

**Вариант A (предпочтительный для MVP):** один draft на весь chat turn.

```
begin_draft(source=AI, request_id=turn_id)
  → execute all tool calls in the turn against draft
  → if all ok: commit_draft (schedule + validate once or per mutation)
  → else: rollback_draft
```

`PlanService.transaction()` уже задаёт этот паттерн.

**Вариант B:** каждая write-tool сама commit. Проще, но хуже для multi-step «перенеси A и зависи B» при частичном фейле.

Выбор MVP: **A** — атомарность пользовательского запроса.

### System prompt (содержание)

- Работай только через tools.
- Сначала `search_tasks` / `get_plan`, если id неизвестны.
- Не выдумывай task_id.
- Даты — ISO; перенос = `move_task`, не «правка start вручную вне tool».
- При ошибке tool — объясни пользователю, не ретрай бесконечно.
- Bulk предпочтительнее N одинаковых single updates.

### LLM provider

Абстракция `LLMClient`:

- `chat(messages, tools) -> assistant message | tool_calls`
- Реализации: OpenAI-compatible HTTP API; `FakeLLM` для тестов.

Env: `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`.

## 5. Валидация действий AI

Многослойная защита:

### Layer 1 — Tool input schemas (Pydantic)

- Типы, required fields, `duration_days >= 1`, date pattern, non-blank names.
- Ошибка → `INVALID_INPUT`, tool не вызывает domain.

### Layer 2 — Domain guards в PlanService

- `TASK_NOT_FOUND`, `UNKNOWN_PREDECESSOR`, `DUPLICATE_TASK`, `INVALID_DURATION`.
- `would_create_cycle` **до** мутации рёбер.

### Layer 3 — Scheduler + assert_valid

Каждый commit path:

```
mutate draft → schedule_plan → assert_valid → save
```

Если финальный план нарушает инварианты — rollback.

### Layer 4 — Agent policy

- Max tool iterations.
- Max tools per turn.
- Reject unknown tool names.
- Не передавать LLM сырой SQL / filesystem.

### Layer 5 — UX honesty

Ошибки возвращаются пользователю текстом; план не меняется при rollback.

## 6. Избежание циклических зависимостей

### Определение

Цикл: путь `A → ... → A` в directed graph `predecessor → successor`  
(ребро: pred ∈ task.predecessor_ids ⇒ pred → task).

### Алгоритмы

1. **`would_create_cycle(plan, successor_id, new_preds)`**  
   Перед установкой рёбер: для каждого нового pred проверить, достижим ли `successor` из pred в обратном/прямом DFS (стандартная проверка back-edge).

2. **Topological sort / Kahn** внутри `schedule_plan` / `validate_plan`  
   Если topo невозможен — `CIRCULAR_DEPENDENCY` (последняя линия обороны).

3. **Self-dependency** запрещена явно (`task_id ∈ predecessor_ids`).

### Где вызывается

- `set_dependencies`
- `create_task` с `predecessor_ids`
- Любой import Excel после построения рёбер

LLM не отвечает за ацикличность — только domain.

## 7. Bulk operations

### Tool: `bulk_update_tasks`

```json
{
  "task_ids": ["task-02", "task-03"],
  "changes": {
    "assignee": "Maya",
    "duration_days": 5,
    "description": null
  }
}
```

Правила:

1. Выполняется внутри **одной** draft transaction.
2. Изменения применяются ко всем id последовательно на копии плана.
3. После всех правок — schedule + validate.
4. Любая ошибка (unknown id, invalid duration) → **полный rollback**.
5. Не смешивать в одном bulk операции с разной семантикой на задачу (для сложных кейсов Agent вызывает несколько tools: move + bulk assignee).

### Bulk через Agent без специального tool?

Возможно N× `set_assignee`, но медленнее и хуже атомарность между LLM round-trips. Dedicated bulk tool обязателен для сценария «массово изменить несколько задач».

### REST зеркало

`POST /api/tasks/bulk` вызывает тот же `PlanService` метод, что и MCP tool.

## 8. Как frontend получает изменения после AI action

1. `POST /api/chat` выполняется синхронно до конца agent turn.
2. Response содержит:
   - `message` (текст ассистента)
   - `plan` (полный актуальный план)
   - `changes` (краткий audit)
3. Chat feature кладёт текст в UI; React Query обновляет cache `['plan']` из `plan`.
4. Gantt ре-рендерится от нового plan.

Нет WebSocket/polling в MVP. «Мгновенно» = сразу после ответа HTTP (обычно < нескольких секунд с LLM).

## 9. Тестирование MCP tools

См. также `implementation-plan.md`.

- Unit: каждый tool — валидный input → ожидаемая мутация; invalid input → `INVALID_INPUT`.
- Cycle cases на `set_dependencies`.
- Bulk rollback: второй id неверный → plan unchanged.
- Без LLM: прямой `MCPServer.call_tool`.

## 10. Тестирование AI agent без реального LLM

`FakeLLM` / scripted client:

```text
ScriptedTurn:
  1) return tool_call search_tasks
  2) return tool_call move_task
  3) return final text
```

Проверяем:

- порядок вызовов;
- commit/rollback;
- финальный plan snapshot;
- текст ответа при ошибке tool.

Отдельно — contract test: tool JSON schemas совместимы с тем, что уходит в LLM provider.
