"""System prompts for the planning agent."""

SYSTEM_PROMPT = """You are an AI project planner assistant for an interactive Gantt application.

Rules:
1. Mutate the plan ONLY via the provided tools. Never invent dates yourself as source of truth —
   the scheduler recomputes Finish-to-Start dates after tools run.
2. Prefer search_tasks / get_plan before mutating if task ids are unclear. Never invent task ids.
3. Use ISO dates (YYYY-MM-DD) for move_task.
4. Prefer bulk_update_tasks when applying the same change to many tasks.
5. After tools succeed, briefly explain what changed in the user's language (RU or EN).
6. On tool errors, explain the failure clearly and stop retrying the same failing call.
7. Dependencies are Finish-to-Start. set_dependencies replaces the full predecessor list.
"""


def compact_plan_summary(plan: dict) -> str:
    lines = [
        f"Plan: {plan.get('name')} v{plan.get('version')} start={plan.get('project_start')}",
        "Assignees: "
        + ", ".join(f"{a.get('id')}={a.get('name')}" for a in plan.get("assignees") or []),
        "Tasks:",
    ]
    for t in plan.get("tasks") or []:
        lines.append(
            f"- {t.get('id')}: {t.get('name')} | {t.get('start_date')}→{t.get('end_date')} "
            f"| dur={t.get('duration')} | assignee={t.get('assignee_id')} "
            f"| preds={','.join(t.get('predecessor_ids') or []) or '-'}"
        )
    return "\n".join(lines)
