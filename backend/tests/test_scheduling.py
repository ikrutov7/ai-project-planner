"""Unit tests for domain scheduling helpers."""

from datetime import date

import pytest

from app.domain.scheduling import (
    compute_end_date,
    earliest_start_after_predecessors,
    would_create_cycle,
)


def test_compute_end_date_inclusive():
    assert compute_end_date(date(2026, 10, 5), 1) == date(2026, 10, 5)
    assert compute_end_date(date(2026, 10, 5), 3) == date(2026, 10, 7)
    assert compute_end_date(date(2026, 10, 5), 5) == date(2026, 10, 9)


def test_compute_end_date_rejects_invalid_duration():
    with pytest.raises(ValueError):
        compute_end_date(date(2026, 10, 5), 0)


def test_earliest_start_without_predecessors():
    assert (
        earliest_start_after_predecessors([], project_start=date(2026, 10, 5))
        == date(2026, 10, 5)
    )


def test_earliest_start_after_predecessors_fs():
    # Pred ends Oct 7 → successor starts Oct 8
    assert earliest_start_after_predecessors(
        [date(2026, 10, 7)],
        project_start=date(2026, 10, 5),
    ) == date(2026, 10, 8)


def test_would_create_cycle_self():
    cycle = would_create_cycle(
        task_id="a",
        predecessor_ids=["a"],
        edges={"a": []},
    )
    assert cycle is not None


def test_would_create_cycle_two_node():
    # a ← b already; adding a as pred of b is fine; adding b as pred of a cycles
    edges = {"a": [], "b": ["a"]}
    assert would_create_cycle(task_id="a", predecessor_ids=["b"], edges=edges) is not None
    assert would_create_cycle(task_id="b", predecessor_ids=["a"], edges={"a": [], "b": []}) is None


def test_would_create_cycle_long_chain():
    edges = {"a": [], "b": ["a"], "c": ["b"], "d": ["c"]}
    cycle = would_create_cycle(task_id="a", predecessor_ids=["d"], edges=edges)
    assert cycle is not None
