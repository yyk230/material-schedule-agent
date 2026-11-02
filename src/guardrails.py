from __future__ import annotations

import re
from typing import Any

from .models import Request
from .store import DraftStore, Session

PUBLISH_CLAIM_RE = re.compile(r"(?<![未不非没])(已发布|发布成功)")
SUMMARY_ORDER = ("incomplete", "blocked", "info_missing", "save_failed", "needs_confirmation", "ready")


def validate_finish(results: list[dict[str, Any]], request: Request, session: Session) -> list[str]:
    """finish 校验 V1-V8，返回错误列表（空表示通过）。"""
    errors: list[str] = []

    # V1
    ids = [r["material_id"] for r in results]
    expected = [it.material_id for it in request.items]
    for mid in expected:
        if ids.count(mid) != 1:
            errors.append(f"V1: 素材 {mid} 必须在 results 中恰好出现一次（实际 {ids.count(mid)} 次）")
    for mid in sorted(set(ids) - set(expected)):
        errors.append(f"V1: {mid} 不在本次请求中")
    if errors:
        return errors

    for r in results:
        mid, decision = r["material_id"], r["decision"]
        item = request.item(mid)
        suggested = r["suggested_time"].strip()
        pending = [p for p in r["pending_confirmations"] if p.strip()]
        check = session.latest_check(mid)
        last_save = session.last_save(mid)

        if decision == "approved":  # V2
            if check is None or check["risk_level"] != "none" or check["missing_fields"]:
                errors.append(f"V2: {mid} 最近一次规则检查不是“无风险且字段完整”，不能 approved")
            if suggested != item.time:
                errors.append(f"V2: {mid} approved 时 suggested_time 必须等于请求时间 {item.time}")
            if pending:
                errors.append(f"V2: {mid} approved 时不能有待确认项")
        if decision == "needs_confirmation" and not pending:  # V3
            errors.append(f"V3: {mid} needs_confirmation 必须列出待确认项")
        if decision == "info_missing":  # V4
            if not ((check and check["missing_fields"]) or session.material_not_found(mid)):
                errors.append(f"V4: {mid} 账本中没有缺失字段或 not_found 记录，不能判 info_missing")
        if item.time_hard and suggested not in ("", item.time):  # V5
            errors.append(f"V5: {mid} 请求时间 {item.time} 为硬性要求，suggested_time 只能为空或 {item.time}")
        if suggested:  # V6
            if last_save is None:
                errors.append(f"V6: {mid} 给出了建议时间 {suggested} 但本次运行没有保存草稿")
            else:
                same_time = last_save["args"].get("time") == suggested
                acceptable = last_save["ok"] or last_save["error"]["code"] == "tool_unavailable"
                if not (same_time and acceptable):
                    errors.append(f"V6: {mid} 最后一次保存与建议时间 {suggested} 不一致或被拒绝")
        if decision in ("blocked", "info_missing"):  # V7
            if any(e["ok"] for e in session.entries("save_schedule_draft", mid)):
                errors.append(f"V7: {mid} 判为 {decision} 但本次运行保存过草稿")
        texts = [r["reason"], *pending]  # V8
        if any(PUBLISH_CLAIM_RE.search(t) for t in texts):
            errors.append(f"V8: {mid} 的文本出现“已发布/发布成功”类表述；本系统只保存草稿")
    return errors


def _draft_info(session: Session, mid: str) -> dict[str, Any]:
    last = session.last_save(mid)
    if last is None:
        return {"status": "not_saved", "draft_id": None, "state": None, "error": None}
    if last["ok"]:
        d = last["data"]
        return {
            "status": "duplicate" if d["duplicate"] else "saved",
            "draft_id": d["draft_id"],
            "state": d["state"],
            "error": None,
        }
    code = last["error"]["code"]
    return {"status": "failed" if code == "tool_unavailable" else "rejected", "draft_id": None, "state": None, "error": code}


def _group(item: dict[str, Any]) -> str:
    status = item["review_status"]
    if status in ("incomplete", "blocked", "info_missing"):
        return status
    if item["draft"]["status"] == "failed":
        return "save_failed"
    if status == "needs_confirmation":
        return "needs_confirmation"
    if status == "approved" and item["draft"]["status"] in ("saved", "duplicate"):
        return "ready"
    return "needs_confirmation"  # approved 但无有效保存的兜底；V6 已阻止此情况


def build_report(
    request: Request,
    session: Session,
    drafts: DraftStore,
    results: list[dict[str, Any]] | None,
    meta: dict[str, Any],
) -> dict[str, Any]:
    """以账本为准组装最终报告。results 为 None 表示 incomplete。"""
    by_id = {r["material_id"]: r for r in (results or [])}
    items = []
    for it in request.items:
        mid = it.material_id
        check = session.latest_check(mid)
        r = by_id.get(mid)
        suggested_time = r["suggested_time"].strip() if r else ""
        suggested_slot = it.slot(suggested_time) if suggested_time else None
        active = drafts.active(mid)
        items.append(
            {
                "material_id": mid,
                "review_status": r["decision"] if r else "incomplete",
                "risk_level": check["risk_level"] if check else None,
                "risk_reasons": [
                    f"{v['rule_id']}: {v['detail']}" for v in (check["violations"] if check else []) if v["rule_id"] != "R001"
                ],
                "missing_fields": list(check["missing_fields"]) if check else [],
                "requested_slot": it.slot(),
                "suggested_slot": suggested_slot,
                "slot_changed": bool(suggested_slot and suggested_time != it.time),
                "pending_confirmations": [p for p in r["pending_confirmations"] if p.strip()] if r else [],
                "draft": _draft_info(session, mid),
                "active_draft": (
                    {"draft_id": active["draft_id"], "time": active["time"], "state": active["state"]} if active else None
                ),
                "publish_status": "not_published",
                "reason": r["reason"] if r else "",
            }
        )
    summary: dict[str, list[str]] = {k: [] for k in SUMMARY_ORDER}
    for item in items:
        summary[_group(item)].append(item["material_id"])
    return {
        "run_status": meta["run_status"],
        "incomplete_reason": meta.get("incomplete_reason"),
        "error": meta.get("error"),
        "request_id": request.request_id,
        "mode": meta["mode"],
        "model": meta["model"],
        "steps_used": meta["steps_used"],
        "tool_calls_used": meta["tool_calls_used"],
        "finish_rejections": meta["finish_rejections"],
        "summary": summary,
        "items": items,
    }
