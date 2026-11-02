"""用按剧本返回的 ScriptedLLM 验证循环边界与防线（模拟真实模型可能出现的错误行为）。"""

from __future__ import annotations

import json

from src.agent import run_once
from src.models import AssistantTurn, RunConfig, ToolCall
from tests.conftest import DATA, SCHEDULE, make_request


class ScriptedLLM:
    model = "scripted"

    def __init__(self, turns):
        self.turns = list(turns)
        self.seen = []  # 每次调用时的 messages 快照

    def complete(self, messages, tools):
        self.seen.append(list(messages))
        if not self.turns:
            return AssistantTurn(content="我想再想想")
        return self.turns.pop(0)


def tc(i, name, **args):
    return ToolCall(id=f"c{i}", name=name, arguments=json.dumps(args, ensure_ascii=False))


def turn(*calls, content=None):
    return AssistantTurn(content=content, tool_calls=list(calls))


def finish_m06(i, decision="approved", reason="已处理"):
    return turn(tc(i, "finish", results=[{"material_id": "M06", "decision": decision, "suggested_time": "10:00",
                                          "pending_confirmations": [], "reason": reason}]))


def cfg(tmp_state, **kw):
    return RunConfig(mode="mock", model="scripted", schedule_path=str(SCHEDULE), state_dir=tmp_state,
                     data_dir=str(DATA), **kw)


def tool_msgs(messages):
    return [m for m in messages if m["role"] == "tool"]


def test_false_save_claim_is_overridden_by_ledger(tmp_state):
    llm = ScriptedLLM([
        turn(tc(1, "check_rules", material_id="M06", reason="检查")),
        turn(tc(2, "save_schedule_draft", material_id="M06", time="10:00", pending_confirmations=[], reason="保存")),
        finish_m06(3, reason="草稿保存成功"),
    ])
    r = run_once(make_request(("M06", "10:00")), llm, cfg(tmp_state, fault="always"))
    m = r.report["items"][0]
    assert r.report["run_status"] == "completed"
    assert m["draft"]["status"] == "failed" and m["draft"]["error"] == "tool_unavailable"
    assert r.report["summary"]["save_failed"] == ["M06"]


def test_text_only_hits_step_limit(tmp_state):
    llm = ScriptedLLM([])
    r = run_once(make_request(("M06", "10:00")), llm, cfg(tmp_state, max_steps=3))
    assert r.report["run_status"] == "incomplete" and r.report["incomplete_reason"] == "max_steps_exceeded"
    assert [s["kind"] for s in r.steps] == ["nudge"] * 3
    assert llm.seen[-1][-1] == {"role": "user", "content": "请调用工具继续，或调用 finish 结束。"}


def test_parallel_calls_beyond_tool_limit_all_answered(tmp_state):
    llm = ScriptedLLM([turn(
        tc(1, "get_material", material_id="M06", reason="a"),
        tc(2, "check_rules", material_id="M06", reason="b"),
        tc(3, "query_slots", material_id="M06", time="10:00", reason="c"),
    )])
    r = run_once(make_request(("M06", "10:00")), llm, cfg(tmp_state, max_tool_calls=1))
    assert r.report["incomplete_reason"] == "max_tool_calls_exceeded"
    assert r.report["tool_calls_used"] == 1
    assert [s["kind"] for s in r.steps] == ["tool", "skipped", "skipped"]
    assert len(r.session.ledger) == 1


def test_parallel_calls_tool_messages_match_ids(tmp_state):
    llm = ScriptedLLM([
        turn(tc(1, "get_material", material_id="M06", reason="a"), tc(2, "check_rules", material_id="M06", reason="b")),
        turn(tc(3, "save_schedule_draft", material_id="M06", time="10:00", pending_confirmations=[], reason="c")),
        finish_m06(4),
    ])
    r = run_once(make_request(("M06", "10:00")), llm, cfg(tmp_state))
    assert r.report["run_status"] == "completed"
    second_call_msgs = llm.seen[1]
    assert [m["tool_call_id"] for m in tool_msgs(second_call_msgs)] == ["c1", "c2"]


def test_finish_with_other_tools_not_counted_as_rejection(tmp_state):
    llm = ScriptedLLM([
        turn(tc(1, "check_rules", material_id="M06", reason="a"),
             tc(2, "finish", results=[])),
        turn(tc(3, "save_schedule_draft", material_id="M06", time="10:00", pending_confirmations=[], reason="b")),
        finish_m06(4),
    ])
    r = run_once(make_request(("M06", "10:00")), llm, cfg(tmp_state))
    assert r.report["run_status"] == "completed" and r.report["finish_rejections"] == 0
    assert "finish_rejected" in [s["kind"] for s in r.steps]


def test_repeated_invalid_finish_ends_incomplete(tmp_state):
    llm = ScriptedLLM([finish_m06(i, decision="approved") for i in range(1, 5)])  # 未检查未保存即 approved
    r = run_once(make_request(("M06", "10:00")), llm, cfg(tmp_state))
    assert r.report["run_status"] == "incomplete" and r.report["incomplete_reason"] == "finish_rejected"
    assert r.report["finish_rejections"] == 3 and r.report["steps_used"] == 3
    rejection = json.loads(tool_msgs(llm.seen[1])[-1]["content"])
    assert any(p.startswith("V2") for p in rejection["error"]["problems"])


def test_invalid_json_and_unknown_tool_continue(tmp_state):
    llm = ScriptedLLM([
        turn(ToolCall(id="c1", name="check_rules", arguments="{bad json")),
        turn(tc(2, "publish_now", material_id="M06", reason="直接发布")),
        turn(tc(3, "check_rules", material_id="M06", reason="重试")),
        turn(tc(4, "save_schedule_draft", material_id="M06", time="10:00", pending_confirmations=[], reason="保存")),
        finish_m06(5),
    ])
    r = run_once(make_request(("M06", "10:00")), llm, cfg(tmp_state))
    assert [s["error_code"] for s in r.steps[:2]] == ["invalid_arguments", "unknown_tool"]
    assert r.steps[1]["args"] == {"material_id": "M06"}
    assert r.report["run_status"] == "completed" and r.report["tool_calls_used"] == 4


def test_llm_exception_reports_incomplete(tmp_state):
    class Boom:
        model = "boom"

        def complete(self, messages, tools):
            raise RuntimeError("network down")

    r = run_once(make_request(("M06", "10:00")), Boom(), cfg(tmp_state))
    assert r.report["incomplete_reason"] == "llm_error" and "network down" in r.report["error"]
