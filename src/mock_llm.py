"""离线 Mock：基于规则的固定策略，仅用于验证循环、工具与防线的流程。

它不代表真实模型的决策效果；真实决策请使用 OpenAICompatLLM 运行并查看 examples/runs/live。
"""

from __future__ import annotations

import json
from typing import Any, Generator

from .models import AssistantTurn, Request, RequestItem, ToolCall

Call = tuple[str, dict[str, Any]]
Policy = Generator[Call, dict[str, Any] | None, Any]


def _result(item: RequestItem, decision: str, suggested: str, pending: list[str], reason: str) -> dict[str, Any]:
    return {
        "material_id": item.material_id,
        "decision": decision,
        "suggested_time": suggested,
        "pending_confirmations": pending,
        "reason": reason,
    }


class MockLLM:
    model = "mock-rule-policy"

    def __init__(self, request: Request):
        self.request = request
        self._policy = self._run()
        self._started = False
        self._seq = 0

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> AssistantTurn:
        last = messages[-1]
        observation = json.loads(last["content"]) if last["role"] == "tool" else None
        name, args = self._policy.send(observation) if self._started else next(self._policy)
        self._started = True
        self._seq += 1
        return AssistantTurn(
            content=None,
            tool_calls=[ToolCall(id=f"mock-{self._seq}", name=name, arguments=json.dumps(args, ensure_ascii=False))],
        )

    # ---- 策略 ----
    def _run(self) -> Policy:
        results = []
        for item in self.request.items:
            results.append((yield from self._handle(item)))
        while True:  # finish 若被打回则原样重交，由循环的打回上限收尾
            yield ("finish", {"results": results})

    @staticmethod
    def _call(item: RequestItem, name: str, reason: str, **args: Any) -> Policy:
        result = yield (name, {"material_id": item.material_id, **args, "reason": reason})
        return result

    def _handle(self, item: RequestItem) -> Policy:
        call = self._call
        r = yield from call(item, "get_material", "先读取素材元数据")
        if not r["ok"]:
            return _result(item, "info_missing", "", [f"素材 {item.material_id} 不存在，请补充素材"], r["error"]["message"])

        r = yield from call(item, "check_rules", "检查审核规则与必填字段")
        check = r["data"]
        if check["missing_fields"]:
            missing = check["missing_fields"]
            yield from call(item, "lookup_material_supplement", f"缺失 {', '.join(missing)}，先补查", fields=missing)
            r = yield from call(item, "check_rules", "补查后重新检查规则")
            check = r["data"]
            if check["missing_fields"]:
                missing = ", ".join(check["missing_fields"])
                return _result(item, "info_missing", "", [f"请补充字段: {missing}"], f"补查后仍缺失 {missing}，不保存草稿")

        if check["risk_level"] == "high":
            details = "；".join(v["detail"] for v in check["violations"] if v["rule_id"] in ("R002", "R004"))
            return _result(item, "blocked", "", [], f"高风险，阻断：{details}")

        requeried = False
        while True:
            r = yield from call(item, "query_slots", f"查询请求时间 {item.time} 是否可用", time=item.time)
            slots = r["data"]
            pending: list[str] = []
            if slots["requested_available"]:
                chosen = item.time
            elif item.time_hard:
                alts = "/".join(slots["alternatives"]) or "无"
                note = f"硬性时段 {item.time} 已被 {slots['occupied_by']} 占用，可选 {alts}，请用户决定"
                return _result(item, "needs_confirmation", "", [note], "请求时间为硬性要求且已被占用，不擅自改时间，不保存草稿")
            elif not slots["alternatives"]:
                note = f"{item.time} 已被 {slots['occupied_by']} 占用，当日无空闲时段，请用户决定"
                return _result(item, "needs_confirmation", "", [note], "当日无可用替代时段，不保存草稿")
            else:
                chosen = slots["alternatives"][0]
                pending.append(f"{item.time} 已被 {slots['occupied_by']} 占用，建议改为 {chosen}，需用户确认")
            if check["risk_level"] == "medium":
                pending.append("版权状态 pending，需确认授权")

            retried = False
            while True:
                reason = f"保存 {chosen} 的草稿" + ("（附待确认项）" if pending else "")
                r = yield from call(item, "save_schedule_draft", reason, time=chosen, pending_confirmations=pending)
                if not r["ok"] and r["error"]["code"] == "tool_unavailable" and not retried:
                    retried = True
                    continue
                break
            if not r["ok"] and r["error"]["code"] == "slot_conflict" and not requeried:
                requeried = True
                continue
            break

        code = None if r["ok"] else r["error"]["code"]
        suggested = chosen if code in (None, "tool_unavailable") else ""
        save_note = "草稿已保存" if code is None else f"草稿保存失败（{code}）"
        if code == "tool_unavailable":
            pending.append(f"草稿保存失败（tool_unavailable），{chosen} 尚未落库，请稍后重试保存或人工录入")
        if pending:
            return _result(item, "needs_confirmation", suggested, pending, f"存在待确认事项；{save_note}")
        return _result(item, "approved", suggested, [], f"无风险，请求时间可用；{save_note}")
