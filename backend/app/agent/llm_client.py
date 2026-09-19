"""LLM client abstractions."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from app.config import Settings


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMClient(Protocol):
    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResponse: ...


class OpenAICompatibleClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self._settings.llm_model,
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self._settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        url = self._settings.llm_base_url.rstrip("/") + "/chat/completions"
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        message = data["choices"][0]["message"]
        tool_calls: list[ToolCall] = []
        for tc in message.get("tool_calls") or []:
            raw_args = tc["function"].get("arguments") or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(
                ToolCall(
                    id=tc.get("id") or f"call_{len(tool_calls)}",
                    name=tc["function"]["name"],
                    arguments=args,
                )
            )
        return LLMResponse(content=message.get("content"), tool_calls=tool_calls)


class ScriptedLLM:
    """Deterministic LLM for tests."""

    def __init__(self, script: list[LLMResponse]) -> None:
        self._script = list(script)
        self._i = 0

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        if self._i >= len(self._script):
            return LLMResponse(content="Done.")
        item = self._script[self._i]
        self._i += 1
        return item
