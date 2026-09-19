# Phase 1 — Deterministic Domain Core

## What was implemented

- Domain models: `Task`, `Plan`, `Dependency`, `Change`
- Structured errors (`TASK_NOT_FOUND`, `CIRCULAR_DEPENDENCY`, …)
- Deterministic FS scheduler (inclusive end dates)
- Plan validator
- `PlanService` (single mutation gateway + draft transactions)
- In-memory `PlanStore` + seeded demo plan (18 tasks)

## What was intentionally NOT implemented

- FastAPI / REST
- Excel import/export
- MCP server
- LLM agent
- React / Gantt

## How to run tests

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

## Architectural decisions (Phase 1)

1. **Inclusive duration:** `end = start + duration_days - 1`.
2. **Move semantics:** soft pin — `start = max(earliest_from_preds, desired)`.
3. **Delete policy:** remove the task id from dependents' predecessor lists.
4. **Draft AI transactions:** `begin_draft` / `commit_draft` / `rollback_draft` and `transaction()` context manager.
5. **Dates are scheduler-owned:** mutations never invent final dates outside `schedule_plan`.

## Architecture review gate

Before Phase 2, run the Architecture Review Prompt against this core.
Phase 2 focus: deeper scheduler↔PlanService integration tests (propagation edge cases).
