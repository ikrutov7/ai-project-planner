# How AI assistants were used

Разработка велась AI-native способом: человек задаёт архитектурные границы и критерии приёмки, ассистент реализует и итерирует.

## Роль ассистента

1. **Архитектура** — зафиксированы слои FastAPI / PlanService / MCP / Agent / React на основе ТЗ и docs.
2. **Домен** — scheduler FS, cycle detection, seed-план, Excel mapping.
3. **MCP + Agent** — typed tools над PlanService; LLM loop + demo-агент без ключа.
4. **Frontend** — Gantt, chat, modal, Excel actions на React + TanStack Query.
5. **Тесты и упаковка** — pytest, Docker multi-stage, README/Roadmap.

## Что делал человек (reviewer)

- Приоритизация MVP vs production backlog
- Проверка UX-сценария: seed → chat → Excel
- Решение по demo-агенту (чтобы демо работало без LLM ключа)
- Финальная проверка README / deploy / артефактов сдачи

## Практики, которые сработали

- Сначала контракты (`docs/architecture.md`, `mcp-tools.md`, `api.md`), потом код
- LLM не считает даты и не пишет в БД — только tools
- Fake/demo agent для тестов без сетевых вызовов к LLM
- Короткий feedback loop: pytest после каждого слоя

## Ограничения

- Ассистент может «переусложнить»; сознательно урезали до single-process MVP
- Визуальный дизайн и демо-gif требуют ручной приёмки
- Production hardening вынесен в `docs/ROADMAP_TO_PRODUCTION.md`
