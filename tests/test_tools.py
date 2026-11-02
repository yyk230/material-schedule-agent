from __future__ import annotations

from src.faults import SaveFault
from tests.conftest import SCHEDULE_ALT, make_request


def call(box, name, step=1, **args):
    return box.execute(name, args, step)


def code(result):
    return None if result["ok"] else result["error"]["code"]


# ---------- 读取 / 补查 / 规则 ----------

def test_supplement_overlay_clears_missing_field(make_box):
    box = make_box(make_request(("M02", "14:00")))
    first = call(box, "check_rules", material_id="M02")["data"]
    assert first["missing_fields"] == ["copyright_status"]
    assert first["violations"][0]["rule_id"] == "R001"

    looked = call(box, "lookup_material_supplement", material_id="M02", fields=["copyright_status"])["data"]
    assert looked == {"found": {"copyright_status": "authorized"}, "still_missing": []}
    assert call(box, "get_material", material_id="M02")["data"]["material"]["copyright_status"] == "authorized"
    assert call(box, "check_rules", material_id="M02")["data"] == {"risk_level": "none", "missing_fields": [], "violations": []}


def test_supplement_not_found_keeps_missing(make_box):
    box = make_box(make_request(("M03", "15:00")))
    looked = call(box, "lookup_material_supplement", material_id="M03", fields=["owner"])["data"]
    assert looked == {"found": {}, "still_missing": ["owner"]}
    assert call(box, "check_rules", material_id="M03")["data"]["missing_fields"] == ["owner"]


def test_rule_levels(make_box):
    box = make_box(make_request(("M04", "16:00"), ("M05", "11:00"), ("M01", "18:00")))
    high = call(box, "check_rules", material_id="M04")["data"]
    assert high["risk_level"] == "high" and high["violations"][0]["rule_id"] == "R002"
    medium = call(box, "check_rules", material_id="M05")["data"]
    assert medium["risk_level"] == "medium" and medium["violations"][0]["rule_id"] == "R003"
    assert call(box, "check_rules", material_id="M01")["data"]["risk_level"] == "none"


def test_material_outside_request_is_not_found(make_box):
    box = make_box(make_request(("M01", "18:00")))
    assert code(call(box, "get_material", material_id="M06")) == "not_found"
    assert code(call(box, "query_slots", material_id="M06", time="10:00")) == "invalid_arguments"


# ---------- 时段查询 ----------

def test_alternatives_order_default_schedule(make_box):
    box = make_box(make_request(("M01", "18:00")))
    d = call(box, "query_slots", material_id="M01", time="18:00")["data"]
    assert d["requested_available"] is False and d["occupied_by"] == "X90"
    assert d["alternatives"] == ["19:00", "17:00", "20:00"]


def test_alternatives_order_alt_schedule(make_box):
    box = make_box(make_request(("M01", "18:00")), schedule=SCHEDULE_ALT)
    assert call(box, "query_slots", material_id="M01", time="18:00")["data"]["alternatives"] == ["20:00", "16:00", "15:00"]


def test_query_out_of_range(make_box):
    box = make_box(make_request(("M01", "18:00")))
    assert code(call(box, "query_slots", material_id="M01", time="23:00")) == "slot_out_of_range"


def test_active_draft_blocks_others_but_not_itself(make_box):
    box = make_box(make_request(("M06", "10:00"), ("M01", "10:00")))
    call(box, "check_rules", material_id="M06")
    assert call(box, "save_schedule_draft", material_id="M06", time="10:00", pending_confirmations=[])["ok"]
    own = call(box, "query_slots", material_id="M06", time="10:00")["data"]
    other = call(box, "query_slots", material_id="M01", time="10:00")["data"]
    assert own["requested_available"] is True
    assert other["requested_available"] is False and other["occupied_by"] == "M06"


# ---------- 保存校验顺序 ----------

def test_save_precondition_requires_check(make_box):
    box = make_box(make_request(("M01", "18:00")))
    assert code(call(box, "save_schedule_draft", material_id="M01", time="19:00", pending_confirmations=["x"])) == "precondition_failed"


def test_save_precondition_missing_and_high(make_box):
    box = make_box(make_request(("M03", "15:00"), ("M04", "16:00")))
    for mid, t in (("M03", "15:00"), ("M04", "16:00")):
        call(box, "check_rules", material_id=mid)
        assert code(call(box, "save_schedule_draft", material_id=mid, time=t, pending_confirmations=["x"])) == "precondition_failed"


def test_save_precondition_requires_recheck_after_supplement(make_box):
    box = make_box(make_request(("M02", "14:00")))
    call(box, "check_rules", material_id="M02")
    call(box, "lookup_material_supplement", material_id="M02", fields=["copyright_status"])
    assert code(call(box, "save_schedule_draft", material_id="M02", time="14:00", pending_confirmations=[])) == "precondition_failed"
    call(box, "check_rules", material_id="M02")
    assert call(box, "save_schedule_draft", material_id="M02", time="14:00", pending_confirmations=[])["ok"]


def test_save_slot_out_of_range_before_hard(make_box):
    box = make_box(make_request(("M07", "18:00", True)))
    call(box, "check_rules", material_id="M07")
    assert code(call(box, "save_schedule_draft", material_id="M07", time="07:00", pending_confirmations=["x"])) == "slot_out_of_range"


def test_save_hard_constraint(make_box):
    box = make_box(make_request(("M07", "18:00", True)))
    call(box, "check_rules", material_id="M07")
    r = call(box, "save_schedule_draft", material_id="M07", time="19:00", pending_confirmations=["用户确认改时间"])
    assert code(r) == "hard_constraint_violation"


def test_save_confirmation_required_for_changed_time(make_box):
    box = make_box(make_request(("M01", "18:00")))
    call(box, "check_rules", material_id="M01")
    assert code(call(box, "save_schedule_draft", material_id="M01", time="19:00", pending_confirmations=[])) == "confirmation_required"
    assert code(call(box, "save_schedule_draft", material_id="M01", time="19:00", pending_confirmations=["  "])) == "confirmation_required"


def test_save_confirmation_required_for_medium_risk(make_box):
    box = make_box(make_request(("M05", "11:00")))
    call(box, "check_rules", material_id="M05")
    assert code(call(box, "save_schedule_draft", material_id="M05", time="11:00", pending_confirmations=[])) == "confirmation_required"
    r = call(box, "save_schedule_draft", material_id="M05", time="11:00", pending_confirmations=["确认授权"])
    assert r["ok"] and r["data"]["state"] == "pending_confirmation"


def test_save_slot_conflict_after_confirmation_check(make_box):
    box = make_box(make_request(("M01", "18:00")))
    call(box, "check_rules", material_id="M01")
    r = call(box, "save_schedule_draft", material_id="M01", time="18:00", pending_confirmations=[])
    assert code(r) == "slot_conflict" and "X90" in r["error"]["message"]


def test_save_check_order_hard_before_confirmation(make_box):
    box = make_box(make_request(("M07", "18:00", True)))
    call(box, "check_rules", material_id="M07")
    assert code(call(box, "save_schedule_draft", material_id="M07", time="19:00", pending_confirmations=[])) == "hard_constraint_violation"


def test_save_check_order_confirmation_before_conflict(make_box):
    box = make_box(make_request(("M05", "18:00")))  # 中风险，且 18:00 被 X90 占用
    call(box, "check_rules", material_id="M05")
    assert code(call(box, "save_schedule_draft", material_id="M05", time="18:00", pending_confirmations=[])) == "confirmation_required"
    assert code(call(box, "save_schedule_draft", material_id="M05", time="18:00", pending_confirmations=["确认授权"])) == "slot_conflict"


def test_save_fault_after_business_checks(make_box):
    box = make_box(make_request(("M01", "18:00")), fault="always")
    call(box, "check_rules", material_id="M01")
    # 业务校验不通过时返回业务错误，而不是故障
    assert code(call(box, "save_schedule_draft", material_id="M01", time="18:00", pending_confirmations=[])) == "slot_conflict"
    assert code(call(box, "save_schedule_draft", material_id="M01", time="19:00", pending_confirmations=["x"])) == "tool_unavailable"
    assert not box.drafts.path.exists()


def test_save_invalid_arguments(make_box):
    box = make_box(make_request(("M01", "18:00")))
    assert code(call(box, "save_schedule_draft", material_id="M01", time="19:00")) == "invalid_arguments"
    assert code(call(box, "save_schedule_draft", material_id="M01", time="7pm", pending_confirmations=[])) == "invalid_arguments"
    assert code(call(box, "query_slots", material_id="M01", time=18)) == "invalid_arguments"


# ---------- 幂等与替换 ----------

def test_idempotent_save_updates_in_place(make_box):
    box = make_box(make_request(("M01", "18:00")))
    call(box, "check_rules", material_id="M01")
    first = call(box, "save_schedule_draft", material_id="M01", time="19:00", pending_confirmations=["a"])["data"]
    second = call(box, "save_schedule_draft", material_id="M01", time="19:00", pending_confirmations=["b"])["data"]
    assert first["draft_id"] == second["draft_id"] == "D-0001"
    assert first["duplicate"] is False and second["duplicate"] is True
    drafts = box.drafts.load()["drafts"]
    assert len(drafts) == 1 and drafts[0]["pending_confirmations"] == ["b"]


def test_idempotent_across_runs(make_box, tmp_state):
    for expected_dup in (False, True):
        box = make_box(make_request(("M01", "18:00")), state_dir=tmp_state)
        call(box, "check_rules", material_id="M01")
        d = call(box, "save_schedule_draft", material_id="M01", time="19:00", pending_confirmations=["a"])["data"]
        assert d["draft_id"] == "D-0001" and d["duplicate"] is expected_dup
    assert len(box.drafts.load()["drafts"]) == 1


def test_changed_slot_supersedes_old_draft(make_box):
    box = make_box(make_request(("M01", "18:00")))
    call(box, "check_rules", material_id="M01")
    call(box, "save_schedule_draft", material_id="M01", time="19:00", pending_confirmations=["a"])
    d = call(box, "save_schedule_draft", material_id="M01", time="20:00", pending_confirmations=["b"])["data"]
    assert d["draft_id"] == "D-0002" and d["superseded"] == ["D-0001"]
    drafts = box.drafts.load()["drafts"]
    assert [x["state"] for x in drafts] == ["superseded", "pending_confirmation"]
    assert box.drafts.active("M01")["draft_id"] == "D-0002"


def test_ready_state_when_unchanged_and_no_pending(make_box):
    box = make_box(make_request(("M06", "10:00")))
    call(box, "check_rules", material_id="M06")
    d = call(box, "save_schedule_draft", material_id="M06", time="10:00", pending_confirmations=[])["data"]
    assert d["state"] == "ready"


# ---------- 故障注入 ----------

def test_fault_modes():
    once, always, none = SaveFault("once"), SaveFault("always"), SaveFault(None)
    assert [once.should_fail() for _ in range(3)] == [True, False, False]
    assert [always.should_fail() for _ in range(3)] == [True, True, True]
    assert [none.should_fail() for _ in range(3)] == [False, False, False]
