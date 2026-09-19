"""Heuristic demo agent used when no LLM API key is configured."""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from app.mcp.tools import MCPServer
from app.schemas import PlanRead


def _find_tasks(plan: PlanRead, query: str) -> list[str]:
    q = query.strip().lower()
    hits = []
    for t in plan.tasks:
        if q in t.name.lower() or q in t.id.lower():
            hits.append(t.id)
    return hits


def run_demo_agent(mcp: MCPServer, user_message: str) -> tuple[str, list[dict[str, Any]]]:
    """
    Parse common RU/EN NL commands into MCP tool calls.
    Returns (assistant_text, tool_trace).
    """
    text = user_message.strip()
    lower = text.lower()
    plan = PlanRead.model_validate(mcp.call_tool("get_plan", {})["data"])
    trace: list[dict[str, Any]] = []

    def call(name: str, args: dict[str, Any]) -> dict[str, Any]:
        result = mcp.call_tool(name, args)
        trace.append({"tool": name, "ok": bool(result.get("success")), "args": args, "result": result})
        return result

    # move task ... by N days / to YYYY-MM-DD
    move_match = re.search(
        r"(?:перенеси|перенести|move)\s+(?:задач[уи]\s+)?[«\"]?(.+?)[»\"]?"
        r"(?:\s+на\s+(\d+)\s+(?:дн|day)|"
        r"\s+(?:на|to)\s+(\d{4}-\d{2}-\d{2})|"
        r"\s+(?:на\s+)?(?:неделю|week)\s+(?:позже|later)|"
        r"\s+(?:на\s+)?(\d+)\s+(?:дн(?:я|ей)?|days?)\s+(?:позже|later))",
        text,
        re.IGNORECASE,
    )
    if move_match or re.search(r"(неделю позже|week later|на неделю)", lower):
        # Extract task name heuristically
        name_match = re.search(
            r"(?:перенеси|перенести|move)\s+(?:задач[уи]\s+)?[«\"]?(.+?)[»\"]?\s+(?:на|to|на неделю|by)",
            text,
            re.IGNORECASE,
        )
        task_query = name_match.group(1).strip() if name_match else ""
        # fallback: known phrases
        if not task_query:
            for t in plan.tasks:
                if t.name.lower() in lower:
                    task_query = t.name
                    break
        ids = _find_tasks(plan, task_query) if task_query else []
        if not ids:
            return (
                "Не нашёл задачу для переноса. Уточните имя, например: "
                "«Перенеси UX Wireframes на 7 дней позже».",
                trace,
            )
        task = next(t for t in plan.tasks if t.id == ids[0])
        days = 7
        m_days = re.search(r"(\d+)\s*(?:дн|day)", lower)
        if m_days:
            days = int(m_days.group(1))
        iso = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        if iso:
            new_start = date.fromisoformat(iso.group(1))
        else:
            new_start = task.start_date + timedelta(days=days)
        result = call("move_task", {"task_id": task.id, "new_start_date": new_start.isoformat()})
        if not result.get("success"):
            return f"Не удалось перенести задачу: {result.get('error')}", trace
        return (
            f"Перенёс «{task.name}» на {new_start.isoformat()}. Диаграмма обновлена.",
            trace,
        )

    # assign X to all ... / назначь X на ...
    assign_match = re.search(
        r"(?:назначь|назначить|assign)\s+([A-Za-zА-Яа-яЁё .'-]+?)\s+(?:на|to)\s+(.+)",
        text,
        re.IGNORECASE,
    )
    if assign_match:
        assignee = assign_match.group(1).strip()
        target = assign_match.group(2).strip()
        ids = _find_tasks(plan, target)
        if "все" in target.lower() or "all" in target.lower() or "design" in target.lower():
            ids = [t.id for t in plan.tasks if "design" in t.name.lower() or "ux" in t.name.lower() or "ui" in t.name.lower()]
            if not ids:
                ids = [t.id for t in plan.tasks]
        if not ids:
            ids = _find_tasks(plan, target)
        if not ids:
            return "Не нашёл задачи для назначения.", trace
        if len(ids) == 1:
            result = call("set_assignee", {"task_id": ids[0], "assignee": assignee})
        else:
            result = call(
                "bulk_update_tasks",
                {"task_ids": ids, "changes": {"assignee": assignee}},
            )
        if not result.get("success"):
            return f"Не удалось назначить: {result.get('error')}", trace
        return f"Назначил {assignee} на {len(ids)} задач(и). Диаграмма обновлена.", trace

    # add / создай задачу
    create_match = re.search(
        r"(?:создай|добавь|create|add)\s+(?:задач[уи]\s+)?(.+)$",
        text,
        re.IGNORECASE,
    )
    if create_match and ("задач" in lower or "task" in lower or "создай" in lower or "добавь" in lower):
        raw_name = create_match.group(1).strip().rstrip(".")
        duration = 3
        dur_tail = re.search(
            r"\s+(?:на|for)\s+(\d+)\s*(?:дн(?:я|ей)?|days?)\s*$",
            raw_name,
            re.IGNORECASE,
        )
        if dur_tail:
            duration = int(dur_tail.group(1))
            raw_name = raw_name[: dur_tail.start()]
        name = raw_name.strip().strip("«»\"'").strip()
        name = re.sub(r"\s+(?:на|for)\s+\d+\s*(?:дн(?:я|ей)?|days?).*$", "", name, flags=re.IGNORECASE).strip()
        if not name:
            return "Укажите имя новой задачи, например: «Создай задачу QA Pass на 2 дня».", trace
        result = call(
            "create_task",
            {"name": name, "description": "Created via chat", "duration_days": duration},
        )
        if not result.get("success"):
            return f"Не удалось создать задачу: {result.get('error')}", trace
        return f"Добавил задачу «{name}» (длительность {duration} дн.).", trace

    # duration change
    dur_match = re.search(
        r"(?:длительност[ьи]|duration).*?(\d+).*?(?:для|for)?\s*[«\"]?(.+?)[»\"]?$",
        text,
        re.IGNORECASE,
    )
    if dur_match or re.search(r"сделай\s+.+\s+\d+\s*дн", lower):
        m = re.search(r"[«\"](.+?)[»\"].*?(\d+)\s*дн", text, re.IGNORECASE) or re.search(
            r"(.+?)\s+(\d+)\s*дн", text, re.IGNORECASE
        )
        if m:
            q, days_s = m.group(1), m.group(2)
            ids = _find_tasks(plan, q.strip())
            if ids:
                result = call("set_duration", {"task_id": ids[0], "duration_days": int(days_s)})
                if result.get("success"):
                    return f"Изменил длительность на {days_s} дн.", trace

    # dependency: сделай X зависимой от Y
    dep_match = re.search(
        r"(?:зависим[аой]+ от|depends on|после)\s+[«\"]?(.+?)[»\"]?\s*$",
        text,
        re.IGNORECASE,
    )
    subject = re.search(
        r"(?:сделай|set)\s+[«\"]?(.+?)[»\"]?\s+(?:зависим|depends|после)",
        text,
        re.IGNORECASE,
    )
    if dep_match and subject:
        child_ids = _find_tasks(plan, subject.group(1))
        parent_ids = _find_tasks(plan, dep_match.group(1))
        if child_ids and parent_ids:
            result = call(
                "set_dependencies",
                {"task_id": child_ids[0], "predecessor_ids": [parent_ids[0]]},
            )
            if result.get("success"):
                return "Обновил зависимости. Диаграмма пересчитана.", trace

    # fallback: summarize plan
    call("get_plan", {})
    return (
        "Я demo-агент (без LLM_API_KEY). Примеры:\n"
        "• Перенеси UX Wireframes на 7 дней позже\n"
        "• Назначь Maya на design\n"
        "• Создай задачу QA Pass на 2 дня\n"
        "• Сделай «Backend API» зависимой от «Scheduler Engine»\n"
        f"Сейчас в плане {len(plan.tasks)} задач, версия {plan.version}.",
        trace,
    )
