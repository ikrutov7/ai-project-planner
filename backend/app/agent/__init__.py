"""Agent orchestration: chat turn → MCP tools → updated plan."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.agent.demo_agent import run_demo_agent
from app.agent.llm_client import LLMClient, LLMResponse, OpenAICompatibleClient, ToolCall
from app.agent.prompts import SYSTEM_PROMPT, compact_plan_summary
from app.config import Settings, get_settings
from app.mcp.tools import MCPServer
from app.schemas import PlanRead
from app.services.plan_service import PlanService


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ChatResult:
    conversation_id: str
    message: ChatMessage
    plan: PlanRead
    changes: list[dict[str, Any]] = field(default_factory=list)
    tool_trace: list[dict[str, Any]] = field(default_factory=list)
    mode: str = "llm"


# In-memory conversation store (MVP)
_CONVERSATIONS: dict[str, list[dict[str, Any]]] = {}


class AgentService:
    def __init__(
        self,
        plan_service: PlanService,
        settings: Settings | None = None,
        llm: LLMClient | None = None,
    ) -> None:
        self._svc = plan_service
        self._settings = settings or get_settings()
        self._mcp = MCPServer(plan_service)
        self._llm = llm

    def handle_chat(
        self,
        message: str,
        *,
        conversation_id: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> ChatResult:
        conv_id = conversation_id or f"conv-{uuid.uuid4().hex[:10]}"
        prior = history if history is not None else list(_CONVERSATIONS.get(conv_id, []))

        if self._llm is not None:
            return self._run_llm(conv_id, message, prior)
        if self._settings.llm_configured:
            self._llm = OpenAICompatibleClient(self._settings)
            return self._run_llm(conv_id, message, prior)
        if self._settings.agent_demo_mode:
            return self._run_demo(conv_id, message, prior)

        plan = self._svc.get_active_plan()
        reply = ChatMessage(
            role="assistant",
            content="LLM не настроен. Укажите PLANNER_LLM_API_KEY или включите demo-режим.",
        )
        return ChatResult(conversation_id=conv_id, message=reply, plan=plan, mode="unconfigured")

    def _run_demo(
        self,
        conv_id: str,
        message: str,
        prior: list[dict[str, Any]],
    ) -> ChatResult:
        text, trace = run_demo_agent(self._mcp, message)
        plan = self._svc.get_active_plan()
        changes = [
            {"op": t["tool"], "ok": t["ok"], "args": t.get("args")}
            for t in trace
            if t["tool"] not in {"get_plan", "get_task", "search_tasks"}
        ]
        reply = ChatMessage(role="assistant", content=text)
        prior = prior + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": text},
        ]
        _CONVERSATIONS[conv_id] = prior[-20:]
        return ChatResult(
            conversation_id=conv_id,
            message=reply,
            plan=plan,
            changes=changes,
            tool_trace=trace,
            mode="demo",
        )

    def _run_llm(
        self,
        conv_id: str,
        message: str,
        prior: list[dict[str, Any]],
    ) -> ChatResult:
        assert self._llm is not None
        plan_snap = self._mcp.call_tool("get_plan", {})["data"]
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "system",
                "content": "Current plan summary:\n" + compact_plan_summary(plan_snap),
            },
        ]
        for m in prior[-12:]:
            messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": message})

        tools = self._mcp.openai_tools()
        trace: list[dict[str, Any]] = []
        changes: list[dict[str, Any]] = []
        final_text = ""

        for _ in range(self._settings.llm_max_iterations):
            response: LLMResponse = self._llm.chat(messages, tools)
            if response.tool_calls:
                messages.append(
                    {
                        "role": "assistant",
                        "content": response.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": json.dumps(tc.arguments),
                                },
                            }
                            for tc in response.tool_calls
                        ],
                    }
                )
                for tc in response.tool_calls:
                    result = self._mcp.call_tool(tc.name, tc.arguments)
                    ok = bool(result.get("success"))
                    trace.append(
                        {
                            "tool": tc.name,
                            "ok": ok,
                            "args": tc.arguments,
                            "result": result,
                        }
                    )
                    if tc.name not in {"get_plan", "get_task", "search_tasks"}:
                        changes.append({"op": tc.name, "ok": ok, "args": tc.arguments})
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(result, default=str),
                        }
                    )
                    if not ok:
                        final_text = (
                            f"Не удалось выполнить {tc.name}: "
                            f"{(result.get('error') or {}).get('message', 'error')}"
                        )
                        break
                if final_text:
                    break
                continue

            final_text = (response.content or "").strip() or "Готово."
            break
        else:
            final_text = final_text or "Достигнут лимит шагов агента."

        plan = self._svc.get_active_plan()
        prior = prior + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": final_text},
        ]
        _CONVERSATIONS[conv_id] = prior[-20:]
        return ChatResult(
            conversation_id=conv_id,
            message=ChatMessage(role="assistant", content=final_text),
            plan=plan,
            changes=changes,
            tool_trace=trace,
            mode="llm",
        )
