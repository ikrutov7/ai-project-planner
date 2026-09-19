# Data Model — Task / Dependency / Plan / Assignee

## 1. Обзор

Каноническая модель живёт на backend (Pydantic). Frontend получает DTO той же формы.

```
Plan
 ├── id, name, project_start, version, updated_at
 ├── tasks: Map<task_id, Task>
 └── recent_changes: Change[]   (audit trail, optional for UI)

Task
 ├── id, name, description
 ├── assignee: string | null     (Assignee как значение, не отдельная сущность в MVP)
 ├── duration_days
 ├── start_date, end_date        (scheduler-owned)
 ├── manual_start                (soft pin after move)
 └── predecessor_ids: string[]

Dependency (projection)
 └── predecessor_id → successor_id, type=FS, lag_days=0
```

## 2. Plan

| Поле | Тип | Описание |
|---|---|---|
| `id` | `string` | `plan-{hex}` |
| `name` | `string` | Название проекта |
| `project_start` | `date` (ISO) | Якорь для задач без предшественников |
| `tasks` | `dict[str, Task]` | Ключ = `task.id` |
| `version` | `int` | Optimistic concurrency / ETag |
| `updated_at` | `datetime` UTC | Последнее изменение |
| `recent_changes` | `Change[]` | Хвост аудита (ограниченный размер, напр. 50) |

### Инварианты Plan

1. Ключи `tasks` совпадают с `task.id`.
2. Все `predecessor_ids` ссылаются на существующие задачи.
3. Граф зависимостей — **DAG** (без циклов).
4. После schedule: у каждой задачи есть `start_date` и `end_date`.
5. Inclusive duration: `end_date = start_date + duration_days - 1`.
6. FS: `start_successor >= end_predecessor + 1 day` (lag=0).

## 3. Task

| Поле | Тип | Описание |
|---|---|---|
| `id` | `string` | Стабильный id (`task-01` в seed; UUID-like в runtime) |
| `name` | `string` | Непустой; уникальность имени — желательна для Excel/AI резолва |
| `description` | `string` | Свободный текст |
| `assignee` | `string \| null` | Имя исполнителя (free-form) |
| `duration_days` | `int ≥ 1` | Календарные дни inclusive |
| `start_date` | `date \| null` | Вычисляется scheduler'ом |
| `end_date` | `date \| null` | Вычисляется scheduler'ом |
| `manual_start` | `date \| null` | Soft pin: `start = max(earliest_FS, manual_start)` |
| `predecessor_ids` | `string[]` | Упорядоченный уникальный список |

### Семантика move

- `move_task` устанавливает `manual_start = desired`.
- Scheduler не даёт стартовать раньше earliest FS.
- Pin сохраняется при последующих reschedule, пока не очищен явно.

### Семантика delete

- Задача удаляется из `tasks`.
- Её id вычищается из `predecessor_ids` всех dependents.
- Downstream пересчитывается.

## 4. Dependency

В persistence **не хранится отдельно** в MVP: рёбра выводятся из `Task.predecessor_ids`.

Проекционная модель для API/валидации:

| Поле | Тип | Default |
|---|---|---|
| `predecessor_id` | `string` | — |
| `successor_id` | `string` | — |
| `type` | `"FS"` | FS only |
| `lag_days` | `int ≥ 0` | `0` |

MVP поддерживает только **Finish-to-Start, lag=0**.

## 5. Assignee

В MVP **не отдельная таблица**.

- `assignee: string | null` на Task.
- Список уникальных исполнителей = `distinct(task.assignee)` для фильтров/подсказок.
- Нормализация имён (trim); case-sensitive display, case-insensitive search optional.

Почему так: нет HR-справочника, Excel приносит произвольные строки. Отдельный `Assignee` entity — post-MVP.

## 6. Change (audit)

| Поле | Тип | Описание |
|---|---|---|
| `id` | `string` | `chg-...` |
| `task_id` | `string \| null` | Затронутая задача |
| `op` | enum | `create_task`, `move_task`, … |
| `field` | `string \| null` | Имя поля при partial update |
| `old_value` / `new_value` | JSON-able | Diff |
| `source` | `ui \| excel \| ai \| system` | Происхождение |
| `request_id` | `string \| null` | Связка AI turn / HTTP request |
| `timestamp` | `datetime` | UTC |

Используется для ответа chat (`changes[]`) и отладки; полный event store не нужен.

## 7. Excel row mapping

Колонки файла:

| Excel | Domain |
|---|---|
| задача | `Task.name` |
| описание | `Task.description` |
| исполнитель | `Task.assignee` |
| длительность | `Task.duration_days` |
| предшественники | `predecessor_ids` (через имена или id — см. import) |

Даты в Excel **не обязательны**: после import всегда `schedule_plan`.

Рекомендация импорта предшественников:

1. Предпочтительный формат: имена задач через `;` или `,`.
2. Альтернатива: id вида `task-01`.
3. Forward references: двухпроходный parse (создать все Task → связать рёбра).

## 8. Persistence mapping (SQLite)

### Рекомендация MVP — document store

```sql
CREATE TABLE plans (
  id TEXT PRIMARY KEY,
  is_active INTEGER NOT NULL DEFAULT 1,
  name TEXT NOT NULL,
  project_start TEXT NOT NULL,   -- ISO date
  version INTEGER NOT NULL,
  updated_at TEXT NOT NULL,       -- ISO datetime
  payload_json TEXT NOT NULL      -- full Plan JSON (tasks + recent_changes)
);
```

- Один active plan (`is_active=1`).
- `save` проверяет `version` и инкрементирует.
- Переход на PostgreSQL: тот же JSONB payload или нормализация без смены `PlanRepository` API.

### Memory store

Тот же `Plan` в RAM для unit/integration тестов без I/O.

## 9. Seed data

- Фабрика `build_seed_plan()` создаёт ~15–20 задач demo-проекта с стабильными id (`task-01` …).
- На старте приложения: если БД пуста → seed → schedule → save.
- Endpoint `POST /api/plan/reset` (опционально, dev) перезагружает seed.

Состав seed должен демонстрировать:

- цепочки зависимостей;
- diamond (несколько preds / dependents);
- разных assignees;
- разную длительность.

## 10. TypeScript DTO (зеркало)

Frontend типы — структурно совместимы с JSON API:

```ts
type Task = {
  id: string;
  name: string;
  description: string;
  assignee: string | null;
  duration_days: number;
  start_date: string; // YYYY-MM-DD
  end_date: string;
  manual_start: string | null;
  predecessor_ids: string[];
};

type Plan = {
  id: string;
  name: string;
  project_start: string;
  version: number;
  updated_at: string;
  tasks: Task[]; // API отдаёт массив; backend внутри dict
};
```

API может отдавать `tasks` как **массив** (удобнее для JSON clients); backend конвертирует dict ↔ list на границе schemas.
