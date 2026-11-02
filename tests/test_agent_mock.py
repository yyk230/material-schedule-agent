"""用 MockLLM 跑运行矩阵（与 scripts/run_examples.py 一致），逐项断言验收预期。"""

from __future__ import annotations

import pytest

from src.main import execute
from src.store import read_json
from tests.conftest import INPUTS, ROOT, SCHEDULE, SCHEDULE_ALT


def run(case, state_dir, **kw):
    kw.setdefault("schedule", str(SCHEDULE))
    _, result = execute(str(INPUTS / case), mock=True, state_dir=state_dir, data_dir=str(ROOT / "data"), **kw)
    return result


def item(result, mid):
    return next(i for i in result.report["items"] if i["material_id"] == mid)


def tool_calls(result, name):
    return [s for s in result.steps if s["tool"] == name]


@pytest.fixture
def conflict_chain(tmp_state):
    """第 2、3、4 次运行：共用 state。"""
    first = run("case02_conflict.json", tmp_state)
    second = run("case02_conflict.json", tmp_state)
    drafts_after_second = read_json(f"{tmp_state}/drafts.json")["drafts"]
    third = run("case02_conflict.json", tmp_state, schedule=str(SCHEDULE_ALT))
    return [first, second, third, read_json(f"{tmp_state}/drafts.json")["drafts"], drafts_after_second]


def test_01_normal(tmp_state):
    r = run("case01_normal.json", tmp_state)
    m = item(r, "M06")
    assert r.report["run_status"] == "completed"
    assert m["review_status"] == "approved" and m["suggested_slot"]["time"] == "10:00"
    assert m["draft"] == {"status": "saved", "draft_id": "D-0001", "state": "ready", "error": None}
    assert r.report["summary"]["ready"] == ["M06"]


def test_02_conflict_reference_case(conflict_chain):
    r = conflict_chain[0]
    m = item(r, "M01")
    assert m["review_status"] == "needs_confirmation"
    assert m["suggested_slot"]["time"] == "19:00" and m["slot_changed"] is True
    assert m["draft"]["status"] == "saved" and m["draft"]["draft_id"] == "D-0001"
    assert m["draft"]["state"] == "pending_confirmation"
    assert m["publish_status"] == "not_published"
    assert any("19:00" in p for p in m["pending_confirmations"])


def test_03_duplicate_submit_single_draft(conflict_chain):
    m = item(conflict_chain[1], "M01")
    assert m["draft"]["status"] == "duplicate" and m["draft"]["draft_id"] == "D-0001"
    assert m["suggested_slot"]["time"] == "19:00"
    drafts = conflict_chain[4]
    assert len(drafts) == 1 and drafts[0]["state"] == "pending_confirmation"


def test_04_slot_changed_resubmit(conflict_chain):
    r, drafts = conflict_chain[2], conflict_chain[3]
    m = item(r, "M01")
    assert m["suggested_slot"]["time"] == "20:00"
    assert m["draft"]["status"] == "saved" and m["draft"]["draft_id"] == "D-0002"
    save = tool_calls(r, "save_schedule_draft")[-1]
    assert "替换 ['D-0001']" in save["summary"]
    assert len(drafts) == 2
    assert [d["draft_id"] for d in drafts if d["state"] != "superseded"] == ["D-0002"]


def test_05_missing_info(tmp_state):
    r = run("case03_missing_info.json", tmp_state)
    m2, m3 = item(r, "M02"), item(r, "M03")
    assert m2["review_status"] == "approved" and m2["draft"]["status"] == "saved" and m2["draft"]["state"] == "ready"
    assert m3["review_status"] == "info_missing" and m3["missing_fields"] == ["owner"]
    assert m3["draft"]["status"] == "not_saved"
    assert len(tool_calls(r, "lookup_material_supplement")) == 2


def test_06_rule_risk(tmp_state):
    r = run("case04_rule_risk.json", tmp_state)
    m4, m5 = item(r, "M04"), item(r, "M05")
    assert m4["review_status"] == "blocked" and m4["risk_level"] == "high"
    assert any(x.startswith("R002") for x in m4["risk_reasons"]) and m4["draft"]["status"] == "not_saved"
    assert m5["review_status"] == "needs_confirmation" and m5["risk_level"] == "medium"
    assert any(x.startswith("R003") for x in m5["risk_reasons"])
    assert m5["suggested_slot"]["time"] == "11:00" and m5["draft"]["state"] == "pending_confirmation"
    m8 = item(r, "M08")
    assert m8["review_status"] == "blocked" and m8["risk_level"] == "high"
    assert any(x.startswith("R004") for x in m8["risk_reasons"]) and m8["draft"]["status"] == "not_saved"
    assert not [s for s in tool_calls(r, "query_slots") if s["args"]["material_id"] in ("M04", "M08")]
    assert r.report["summary"]["blocked"] == ["M04", "M08"]


def test_07_hard_conflict(tmp_state):
    r = run("case05_hard_conflict.json", tmp_state)
    m = item(r, "M07")
    assert m["review_status"] == "needs_confirmation" and m["suggested_slot"] is None
    assert m["draft"]["status"] == "not_saved" and not tool_calls(r, "save_schedule_draft")
    assert any("19:00" in p for p in m["pending_confirmations"])


def test_08_save_fail_always(tmp_state):
    r = run("case01_normal.json", tmp_state, fault="save=always")
    m = item(r, "M06")
    assert m["review_status"] == "needs_confirmation" and m["suggested_slot"]["time"] == "10:00"
    assert any("草稿保存失败" in p for p in m["pending_confirmations"])
    assert m["draft"] == {"status": "failed", "draft_id": None, "state": None, "error": "tool_unavailable"}
    assert m["active_draft"] is None
    assert len(tool_calls(r, "save_schedule_draft")) == 2
    assert r.report["summary"]["save_failed"] == ["M06"]


def test_09_save_fail_once(tmp_state):
    r = run("case01_normal.json", tmp_state, fault="save=once")
    m = item(r, "M06")
    saves = tool_calls(r, "save_schedule_draft")
    assert [s["error_code"] for s in saves] == ["tool_unavailable", None]
    assert m["draft"]["status"] == "saved" and r.report["summary"]["ready"] == ["M06"]


def test_10_step_limit(tmp_state):
    r = run("case03_missing_info.json", tmp_state, max_steps=2)
    assert r.report["run_status"] == "incomplete" and r.report["incomplete_reason"] == "max_steps_exceeded"
    assert r.report["steps_used"] == 2
    assert r.report["summary"]["incomplete"] == ["M02", "M03"]
