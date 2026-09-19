"""Scheduling helpers: dates, FS earliest start, cycle detection.

Business rules live here (and in the service), not in repositories or API routes.
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import date, timedelta
from typing import Iterable


def compute_end_date(start_date: date, duration: int) -> date:
    """Inclusive duration: duration=1 → end==start; duration=3 → start..start+2."""
    if duration < 1:
        raise ValueError("duration must be >= 1")
    return start_date + timedelta(days=duration - 1)


def earliest_start_after_predecessors(
    predecessor_end_dates: Iterable[date],
    *,
    project_start: date,
) -> date:
    """Finish-to-Start, lag=0: start = max(project_start, max(pred_end)+1)."""
    ends = list(predecessor_end_dates)
    if not ends:
        return project_start
    return max(project_start, max(ends) + timedelta(days=1))


def would_create_cycle(
    *,
    task_id: str,
    predecessor_ids: list[str],
    edges: dict[str, list[str]],
) -> list[str] | None:
    """Return a cycle path if adding predecessors for task_id would create a cycle.

    ``edges`` maps successor_id → list of predecessor_ids (current graph).
    """
    for pred in predecessor_ids:
        if pred == task_id:
            return [task_id, task_id]
        # Walk forward from task_id along successor links; if we reach pred, cycle.
        # Build adjacency: pred → successors
        successors: dict[str, list[str]] = defaultdict(list)
        for succ, preds in edges.items():
            for p in preds:
                successors[p].append(succ)
        # Tentatively add edges pred → task_id for each new pred
        for p in predecessor_ids:
            successors[p].append(task_id)

        path = _find_path(successors, start=task_id, target=pred)
        if path is not None:
            return path + [pred]
    return None


def _find_path(
    successors: dict[str, list[str]],
    *,
    start: str,
    target: str,
) -> list[str] | None:
    stack: list[tuple[str, list[str]]] = [(start, [start])]
    visited: set[str] = set()
    while stack:
        node, path = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        for nxt in successors.get(node, []):
            if nxt == target:
                return path + [nxt]
            if nxt not in visited:
                stack.append((nxt, path + [nxt]))
    return None


def topological_order(task_ids: Iterable[str], edges: dict[str, list[str]]) -> list[str]:
    """Kahn topo sort. edges: successor → predecessors. Raises ValueError on cycle."""
    ids = list(task_ids)
    preds: dict[str, set[str]] = {tid: set(edges.get(tid, [])) for tid in ids}
    dependents: dict[str, list[str]] = defaultdict(list)
    for tid, pred_set in preds.items():
        for p in pred_set:
            dependents[p].append(tid)

    queue: deque[str] = deque(sorted(tid for tid, ps in preds.items() if not ps))
    order: list[str] = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for dep in dependents.get(node, []):
            preds[dep].discard(node)
            if not preds[dep]:
                queue.append(dep)

    if len(order) != len(ids):
        raise ValueError("Dependency cycle detected")
    return order
