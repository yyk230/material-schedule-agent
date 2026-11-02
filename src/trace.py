from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .agent import RunResult
from .models import Request
from .store import write_json

MOCK_NOTICE = "> Mock 为规则策略，仅验证流程，不代表真实模型的决策效果。"


def _cell(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return (text or "").replace("|", "\\|").replace("\n", " ")


def item_line(item: dict[str, Any]) -> str:
    slot = item["suggested_slot"]["time"] if item["suggested_slot"] else "-"
    draft = item["draft"]
    draft_text = draft["status"] + (f" {draft['draft_id']}" if draft["draft_id"] else "") + (
        f" ({draft['error']})" if draft["error"] else ""
    )
    return (
        f"{item['material_id']}: {item['review_status']} | 风险 {item['risk_level']} | "
        f"请求 {item['requested_slot']['time']} -> 建议 {slot} | 草稿 {draft_text} | {item['publish_status']}"
    )


def render_markdown(request: Request, result: RunResult) -> str:
    report, steps = result.report, result.steps
    lines = [
        f"# Run {report['request_id']}",
        "",
        f"- mode: `{report['mode']}`，model: `{report['model']}`",
        f"- run_status: `{report['run_status']}`" + (f"，原因: `{report['incomplete_reason']}`" if report["incomplete_reason"] else ""),
        f"- steps_used: {report['steps_used']}，tool_calls_used: {report['tool_calls_used']}，finish_rejections: {report['finish_rejections']}",
        f"- config: `{json.dumps(result.config, ensure_ascii=False)}`",
    ]
    if report["error"]:
        lines.append(f"- error: `{report['error']}`")
    if report["mode"] == "mock":
        lines += ["", MOCK_NOTICE]
    lines += [
        "",
        "## 请求",
        "",
        "```json",
        json.dumps(request.to_dict(), ensure_ascii=False, indent=2),
        "```",
        "",
        "## 执行步骤",
        "",
        "| 步骤 | 动作 | 参数 | 依据 | 返回摘要 | 后续动作 |",
        "|---|---|---|---|---|---|",
    ]
    for i, s in enumerate(steps):
        action = s["tool"] or s["kind"]
        if s["tool"] and s["kind"] not in ("tool", s["tool"]):
            action = f"{s['tool']} ({s['kind']})"
        if i + 1 < len(steps):
            nxt = steps[i + 1]["tool"] or steps[i + 1]["kind"]
        elif report["run_status"] == "completed":
            nxt = "结束：" + "，".join(f"{it['material_id']}={it['review_status']}" for it in report["items"])
        else:
            nxt = f"结束：incomplete（{report['incomplete_reason']}）"
        args = s["args"]
        if s["tool"] == "finish" and isinstance(args, dict):
            args = "见最终报告"
        reason = s["reason"] or (f"模型说明: {s['model_note']}" if s["model_note"] else "")
        lines.append(
            f"| {s['step']} | {_cell(action)} | {_cell(args) if args is not None else ''} | {_cell(reason)} | {_cell(s['summary'])} | {_cell(nxt)} |"
        )
    lines += ["", "## 最终报告", ""]
    lines += [f"- {item_line(it)}" for it in report["items"]]
    lines += ["", f"summary: `{json.dumps(report['summary'], ensure_ascii=False)}`", "", "```json",
              json.dumps(report, ensure_ascii=False, indent=2), "```", ""]
    return "\n".join(lines)


def write_outputs(out_dir: str | Path, request: Request, result: RunResult) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_json(
        out / "run.json",
        {"request": request.to_dict(), "config": result.config, "steps": result.steps, "report": result.report},
    )
    (out / "run.md").write_text(render_markdown(request, result), encoding="utf-8")
    drafts = Path(result.state_dir) / "drafts.json"
    if drafts.exists():
        shutil.copyfile(drafts, out / "drafts.json")
    return out
