from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

DECISIONS = ("approved", "needs_confirmation", "info_missing", "blocked")
REVIEW_STATUSES = DECISIONS + ("incomplete",)
DRAFT_STATES = ("ready", "pending_confirmation", "superseded")
DRAFT_STATUSES = ("saved", "duplicate", "failed", "rejected", "not_saved")

ERROR_CODES = (
    "not_found",
    "invalid_arguments",
    "unknown_tool",
    "tool_unavailable",
    "precondition_failed",
    "confirmation_required",
    "hard_constraint_violation",
    "slot_conflict",
    "slot_out_of_range",
    "skipped",
)

TIME_RE = re.compile(r"^\d{2}:\d{2}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class RequestItem:
    material_id: str
    channel: str
    date: str
    time: str
    time_hard: bool = False

    def slot(self, time: str | None = None) -> dict[str, str]:
        return {"channel": self.channel, "date": self.date, "time": time or self.time}


@dataclass
class Request:
    request_id: str
    items: list[RequestItem]

    def item(self, material_id: str) -> RequestItem | None:
        for it in self.items:
            if it.material_id == material_id:
                return it
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "items": [
                {
                    "material_id": it.material_id,
                    "channel": it.channel,
                    "date": it.date,
                    "time": it.time,
                    "time_hard": it.time_hard,
                }
                for it in self.items
            ],
        }


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # 原始 JSON 字符串，解析失败由循环处理


@dataclass
class AssistantTurn:
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass
class RunConfig:
    mode: str = "mock"  # mock | live
    model: str = "mock-rule-policy"
    max_steps: int = 20
    max_tool_calls: int = 40
    max_finish_rejections: int = 2
    fault: str | None = None  # None | once | always，仅作用于保存工具
    schedule_path: str = "data/schedule.json"
    state_dir: str = ""
    data_dir: str = "data"


def ok(data: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "data": data}


def err(code: str, message: str) -> dict[str, Any]:
    assert code in ERROR_CODES, code
    return {"ok": False, "error": {"code": code, "message": message}}
