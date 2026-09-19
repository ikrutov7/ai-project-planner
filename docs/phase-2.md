# Phase 2 — Scheduler ↔ PlanService Integration

## What was implemented

- Sticky schedule pins via `Task.manual_start` (set by `move_task`)
- Scheduler resolves `start = max(earliest_FS, manual_start | desired_start)`
- `would_create_cycle` / `collect_downstream` helpers
- FS consistency checks in `validate_plan`
- `PlanService._finalize` as the single schedule → validate → persist/draft path
- Draft mutations work on copies (failed ops cannot corrupt draft/store)
- `clear_manual_start` to re-anchor a task to earliest FS
- Comprehensive propagation and cycle tests

## Why this layer

Phase 1 could lose an intentional task delay on the next full reschedule.
Phase 2 makes move intent part of the domain model so Excel/UI/AI share the same pin semantics.

## Tests

```bash
cd backend && source .venv/bin/activate && pytest -q
```

Coverage added in `tests/test_scheduler_phase2.py`:

- chain / diamond propagation
- duration → downstream dates
- circular detection (2-node, long)
- `would_create_cycle` back-edge rejection
- manual_start survives later mutations
- soft clamp when preds push past pin
- draft scheduled preview + failed mutation isolation

## Not in Phase 2

- Excel, MCP, LLM, FastAPI, React
