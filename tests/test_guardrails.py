from __future__ import annotations

import pytest

from src.guardrails import build_report, validate_finish
from tests.conftest import make_request

META = {"run_status": "completed", "mode": "mock", "model": "t", "steps_used": 1, "tool_calls_used": 1, "finish_rejections": 0}


def res(mid, decision, time="", pending=None, reason="理由"):
    return {"material_id": mid, "decision": decision, "suggested_time": time,
            "pending_confirmations": pending or [], "reason": reason}


def call(box, name, **args):
    return box.execute(name, args, 1)


def rules_of(errors):
    return {e.split(":")[0] for e in errors}


@pytest.fixture
def conflict_box(make_box):
    """M01 18:00 被占，已保存 19:00 待确认草稿。"""
    box = make_box(make_request(("M01", "18:00")))
    call(box, "check_rules", material_id="M01")
    call(box, "save_schedule_draft", material_id="M01", time="19:00", pending_confirmations=["改 19:00 待确认"])
    return box


def test_valid_conflict_result_passes(conflict_box):
    ok = [res("M01", "needs_confirmation", "19:00", ["改 19:00 待确认"])]
    assert validate_finish(ok, conflict_box.request, conflict_box.session) == []


def test_v1_missing_duplicate_and_extra(conflict_box):
    s, rq = conflict_box.session, conflict_box.request
    assert rules_of(validate_finish([], rq, s)) == {"V1"}
    two = [res("M01", "needs_confirmation", "19:00", ["x"])] * 2
    assert rules_of(validate_finish(two, rq, s)) == {"V1"}
    extra = [res("M01", "needs_confirmation", "19:00", ["x"]), res("M99", "blocked")]
    assert rules_of(validate_finish(extra, rq, s)) == {"V1"}


def test_v2_approved_with_changed_slot_rejected(conflict_box):
    errors = validate_finish([res("M01", "approved", "19:00")], conflict_box.request, conflict_box.session)
    assert "V2" in rules_of(errors)


def test_v2_approved_with_risk_rejected(make_box):
    box = make_box(make_request(("M05", "11:00")))
    call(box, "check_rules", material_id="M05")
    call(box, "save_schedule_draft", material_id="M05", time="11:00", pending_confirmations=["确认授权"])
    assert "V2" in rules_of(validate_finish([res("M05", "approved", "11:00")], box.request, box.session))
    assert validate_finish([res("M05", "needs_confirmation", "11:00", ["确认授权"])], box.request, box.session) == []


def test_v3_needs_confirmation_requires_pending(conflict_box):
    errors = validate_finish([res("M01", "needs_confirmation", "19:00", ["  "])], conflict_box.request, conflict_box.session)
    assert rules_of(errors) == {"V3"}


def test_v4_info_missing_requires_evidence(make_box):
    box = make_box(make_request(("M01", "18:00"), ("M03", "15:00")))
    call(box, "check_rules", material_id="M01")
    call(box, "check_rules", material_id="M03")
    results = [res("M01", "info_missing", pending=["x"]), res("M03", "info_missing", pending=["补 owner"])]
    errors = validate_finish(results, box.request, box.session)
    assert len(errors) == 1 and errors[0].startswith("V4: M01")


def test_v4_accepts_not_found(make_box):
    box = make_box(make_request(("M99", "10:00")))
    call(box, "get_material", material_id="M99")
    assert validate_finish([res("M99", "info_missing", pending=["素材不存在"])], box.request, box.session) == []


def test_v5_hard_time(make_box):
    box = make_box(make_request(("M07", "18:00", True)))
    call(box, "check_rules", material_id="M07")
    errors = validate_finish([res("M07", "needs_confirmation", "19:00", ["x"])], box.request, box.session)
    assert "V5" in rules_of(errors)
    assert validate_finish([res("M07", "needs_confirmation", "", ["可选 19:00"])], box.request, box.session) == []


def test_v6_suggested_requires_matching_save(conflict_box):
    errors = validate_finish([res("M01", "needs_confirmation", "20:00", ["x"])], conflict_box.request, conflict_box.session)
    assert rules_of(errors) == {"V6"}


def test_v6_rejected_save_does_not_count(make_box):
    box = make_box(make_request(("M01", "18:00")))
    call(box, "check_rules", material_id="M01")
    call(box, "save_schedule_draft", material_id="M01", time="19:00", pending_confirmations=[])  # confirmation_required
    errors = validate_finish([res("M01", "needs_confirmation", "19:00", ["x"])], box.request, box.session)
    assert rules_of(errors) == {"V6"}


def test_v6_accepts_tool_unavailable(make_box):
    box = make_box(make_request(("M06", "10:00")), fault="always")
    call(box, "check_rules", material_id="M06")
    call(box, "save_schedule_draft", material_id="M06", time="10:00", pending_confirmations=[])
    assert validate_finish([res("M06", "approved", "10:00")], box.request, box.session) == []


def test_v7_blocked_with_saved_draft(conflict_box):
    errors = validate_finish([res("M01", "blocked", "", reason="阻断")], conflict_box.request, conflict_box.session)
    assert rules_of(errors) == {"V7"}


def test_v7_blocked_without_save_passes(make_box):
    box = make_box(make_request(("M04", "16:00")))
    call(box, "check_rules", material_id="M04")
    call(box, "save_schedule_draft", material_id="M04", time="16:00", pending_confirmations=[])  # precondition_failed
    assert validate_finish([res("M04", "blocked", reason="高风险")], box.request, box.session) == []


@pytest.mark.parametrize(
    "text,bad",
    [("素材已发布", True), ("草稿发布成功", True), ("尚未发布，仅保存草稿", False), ("未发布", False), ("暂未发布", False), ("没发布成功", False)],
)
def test_v8_publish_claims(conflict_box, text, bad):
    errors = validate_finish([res("M01", "needs_confirmation", "19:00", ["x"], reason=text)],
                             conflict_box.request, conflict_box.session)
    assert ("V8" in rules_of(errors)) is bad


def test_report_fields_come_from_ledger(make_box):
    box = make_box(make_request(("M06", "10:00")), fault="always")
    call(box, "check_rules", material_id="M06")
    call(box, "save_schedule_draft", material_id="M06", time="10:00", pending_confirmations=[])
    # 模型在 reason 里声称保存成功也不影响 draft 字段
    report = build_report(box.request, box.session, box.drafts, [res("M06", "approved", "10:00", reason="草稿保存成功")], META)
    item = report["items"][0]
    assert item["draft"] == {"status": "failed", "draft_id": None, "state": None, "error": "tool_unavailable"}
    assert item["active_draft"] is None and item["publish_status"] == "not_published"
    assert item["risk_level"] == "none" and item["slot_changed"] is False
    assert report["summary"]["save_failed"] == ["M06"] and report["summary"]["ready"] == []


def test_report_conflict_item(conflict_box):
    report = build_report(conflict_box.request, conflict_box.session, conflict_box.drafts,
                          [res("M01", "needs_confirmation", "19:00", ["改 19:00 待确认"])], META)
    item = report["items"][0]
    assert item["slot_changed"] is True
    assert item["suggested_slot"] == {"channel": "douyin", "date": "2026-11-05", "time": "19:00"}
    assert item["draft"]["status"] == "saved" and item["active_draft"]["draft_id"] == "D-0001"
    assert report["summary"]["needs_confirmation"] == ["M01"]


def test_report_incomplete(make_box):
    box = make_box(make_request(("M04", "16:00"), ("M06", "10:00")))
    call(box, "check_rules", material_id="M04")
    report = build_report(box.request, box.session, box.drafts, None,
                          {**META, "run_status": "incomplete", "incomplete_reason": "max_steps_exceeded"})
    assert [i["review_status"] for i in report["items"]] == ["incomplete", "incomplete"]
    assert report["items"][0]["risk_level"] == "high" and report["items"][1]["risk_level"] is None
    assert report["summary"]["incomplete"] == ["M04", "M06"]


def test_summary_priority(make_box):
    box = make_box(make_request(("M04", "16:00"), ("M03", "15:00"), ("M06", "10:00"), ("M01", "18:00")))
    for mid in ("M04", "M03", "M06", "M01"):
        call(box, "check_rules", material_id=mid)
    call(box, "save_schedule_draft", material_id="M06", time="10:00", pending_confirmations=[])
    call(box, "save_schedule_draft", material_id="M01", time="19:00", pending_confirmations=["x"])
    results = [res("M04", "blocked"), res("M03", "info_missing", pending=["补 owner"]),
               res("M06", "approved", "10:00"), res("M01", "needs_confirmation", "19:00", ["x"])]
    summary = build_report(box.request, box.session, box.drafts, results, META)["summary"]
    assert summary == {"incomplete": [], "blocked": ["M04"], "info_missing": ["M03"], "save_failed": [],
                       "needs_confirmation": ["M01"], "ready": ["M06"]}
