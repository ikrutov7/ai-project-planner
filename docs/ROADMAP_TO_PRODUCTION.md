# Roadmap to Production

Документ описывает, что сознательно оставлено за рамками MVP и в каком порядке закрывать долги, чтобы довести AI Project Planner до боевого состояния.

## 1. Что есть в MVP

- Seed-план (~20 задач) при старте
- Интерактивный Gantt + модалка задачи
- Excel import/export (колонки: задача, описание, исполнитель, длительность, предшественники)
- AI chat → MCP tools → PlanService (даты считает scheduler, не LLM)
- Demo-агент без API-ключа + OpenAI-compatible LLM при наличии ключа
- SQLite persistence, single-process FastAPI

## 2. Сознательные упрощения / техдолг

| Область | Сейчас | Риск |
|---|---|---|
| AuthN/AuthZ | Нет | Любой с URL может менять план |
| Multi-tenancy | Один активный план | Нельзя изолировать проекты/команды |
| Concurrency | Last-write-wins | Потеря правок при параллельных сессиях |
| Conversations | In-memory dict | История чата теряется при рестарте |
| Draft transactions | Commit per tool | Частичные AI-мутации при mid-turn failure (частично смягчено сообщениями об ошибке) |
| Working calendar | Calendar days | Нет учёта выходных/праздников |
| Observability | Базовые логи | Нет метрик/трейсинга chat turns |
| LLM safety | System prompt + domain validation | Нет budget/rate limit, нет human-in-the-loop confirm |
| Frontend | Client-side only SPA | Нет E2E в CI, нет a11y audit |
| Storage | SQLite file | Не для multi-instance / horizontal scale |
| CORS | Открытый список из env | Нужно ужесточить под конкретные origin |

## 3. Чего не хватает для продакшена

1. **Безопасность:** JWT/OIDC, роли (viewer/editor/admin), audit log мутаций.
2. **Данные:** PostgreSQL, миграции как единственный путь schema, бэкапы, soft-delete.
3. **Надёжность AI:** атомарный draft на весь chat-turn; idempotency keys; подтверждение destructive ops; cost/latency limits.
4. **Продукт:** undo/redo, версии плана, комментарии, уведомления, multi-plan workspace.
5. **UX:** drag-and-drop на Gantt, критический путь, фильтры по исполнителю, i18n.
6. **Ops:** structured logging + request_id, OpenTelemetry, health/readiness probes, autoscaling, secrets manager.
7. **Качество:** Playwright E2E в CI, contract tests OpenAPI, load test chat+import.
8. **Compliance:** retention policy для chat, PII scrubbing в LLM prompts.

## 4. Порядок закрытия (рекомендуемый)

### Phase P0 — Soft launch (1–2 недели)

1. Auth (хотя бы magic-link / OIDC) + per-user plan ownership
2. PostgreSQL + Alembic-only migrations
3. Optimistic locking (`expected_version`) на мутациях
4. Rate limit на `/api/chat` и `/api/excel/import`
5. Атомарный draft transaction на chat turn
6. Жёсткий CORS + HTTPS only

### Phase P1 — Team usage (2–4 недели)

1. Multi-plan workspace + sharing
2. Persist chat history
3. Undo stack / plan snapshots
4. Working-day calendar
5. Metrics: tool success rate, LLM latency, import failures
6. Playwright happy-path в CI

### Phase P2 — Scale & polish

1. Horizontal API (stateless) + managed Postgres
2. Streaming chat (SSE)
3. Advanced Gantt (drag, critical path, baselines)
4. Human approval for bulk destructive AI actions
5. Data export/GDPR erase

## 5. Риски

- **LLM hallucinated IDs** — уже смягчено tools + search; в проде добавить grounding checks.
- **Excel garbage-in** — fail-closed на циклы; нужны лимиты размера/строк и malware scan на upload.
- **Cost runaway** — без лимитов токенов агент может крутиться; нужен max iterations (есть) + $ budget.
- **SQLite locking** — под нагрузкой заменить на Postgres до появления второго инстанса.
- **Demo agent divergence** — heuristic path ≠ LLM path; в проде demo выключать или явно маркировать.

## 6. Definition of Done для production

- [ ] Auth + RBAC
- [ ] Postgres + backups
- [ ] Atomic AI transactions + audit log
- [ ] E2E + load tests green
- [ ] Observability dashboards
- [ ] Runbook (incident, key rotation, restore)
- [ ] Security review (deps, upload, prompt injection)
