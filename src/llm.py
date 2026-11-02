from __future__ import annotations

import os
from typing import Any, Protocol

from .models import AssistantTurn, ToolCall


class LLM(Protocol):
    model: str

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> AssistantTurn: ...


class OpenAICompatLLM:
    """OpenAI 兼容 Chat Completions + function calling。"""

    def __init__(self, api_key: str, model: str, base_url: str | None = None, temperature: str | None = "0"):
        from openai import OpenAI

        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url or None, timeout=60, max_retries=2)
        self.temperature = float(temperature) if temperature not in (None, "") else None

    @classmethod
    def from_env(cls) -> "OpenAICompatLLM":
        return cls(
            api_key=os.environ["OPENAI_API_KEY"],
            model=os.environ["MODEL_NAME"],
            base_url=os.environ.get("OPENAI_BASE_URL") or None,
            temperature=os.environ.get("LLM_TEMPERATURE", "0"),
        )

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> AssistantTurn:
        kwargs: dict[str, Any] = {"model": self.model, "messages": messages, "tools": tools, "tool_choice": "auto"}
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        resp = self.client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        calls = [
            ToolCall(id=tc.id, name=tc.function.name, arguments=tc.function.arguments or "{}")
            for tc in (msg.tool_calls or [])
        ]
        return AssistantTurn(content=msg.content, tool_calls=calls)
