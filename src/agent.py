from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .faults import SaveFault
from .guardrails import build_report, validate_finish
from .llm import LLM
from .models import AssistantTurn, Request, RunConfig, ToolCall, err
from .prompts import SYSTEM_PROMPT, build_user_message
from .store import Dataset, DraftStore, Session
from .tools import TOOL_NAMES, TOOL_SCHEMAS, ToolBox, summarize, validate_args

NUDGE = "请调用工具继续，或调用 finish 结束。"


@dataclass
class RunResult:
    report: dict[str, Any]
    steps: list[dict[str, Any]]
    config: dict[str, Any]
    state_dir: str = ""
    session: Session = field(repr=False, default_factory=Session)


def _assistant_message(turn: AssistantTurn) -> dict[str, Any]:
    msg: dict[str, Any] = {"role": "assistant", "content": turn.content}
    if turn.tool_calls:
        msg["tool_calls"] = [
            {"id": tc.id, "type": "function", "function": {"name": tc.name, "arguments": tc.arguments}}
            for tc in turn.tool_calls
        ]
    return msg


def _tool_message(tc: ToolCall, payload: dict[str, Any]) -> dict[str, Any]:
    return {"role": "tool", "tool_call_id": tc.id, "content": json.dumps(payload, ensure_ascii=False)}


def _display_path(path: str) -> str:
    """写入 trace 的路径：仓库内用相对路径，仓库外（临时目录）不暴露本机绝对路径。"""
    p = Path(path).resolve()
    try:
        return p.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return "<tempdir>"


def _parse_args(raw: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        args = json.loads(raw or "{}")
    except json.JSONDecodeError as e:
        return None, f"参数不是合法 JSON: {e.msg}"
    if not isinstance(args, dict):
        return None, "参数必须是 JSON 对象"
    return args, None


def run_once(request: Request, llm: LLM, config: RunConfig) -> RunResult:
    dataset = Dataset.load(config.data_dir, config.schedule_path)
    session = Session()
    drafts = DraftStore(config.state_dir)
    toolbox = ToolBox(dataset, request, session, drafts, SaveFault(config.fault))

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_message(request)},
    ]
    steps: list[dict[str, Any]] = []
    steps_used = tool_calls_used = rejections = 0
    results: list[dict[str, Any]] | None = None
    incomplete_reason: str | None = None
    error: str | None = None

    def trace(step: int, kind: str, **kw: Any) -> None:
        entry = {
            "step": step,
            "kind": kind,
            "tool": kw.get("tool"),
            "args": kw.get("args"),
            "reason": kw.get("reason", ""),
            "ok": kw.get("ok"),
            "summary": kw.get("summary", ""),
            "error_code": kw.get("error_code"),
            "model_note": kw.get("model_note"),
        }
        steps.append(entry)

    while True:
        if steps_used >= config.max_steps:
            incomplete_reason = "max_steps_exceeded"
            break
        steps_used += 1
        step = steps_used
        try:
            turn = llm.complete(messages, TOOL_SCHEMAS)
        except Exception as e:  # noqa: BLE001 - 任何模型调用异常都以 incomplete 收尾
            incomplete_reason = "llm_error"
            error = f"{type(e).__name__}: {e}"[:300]
            break

        note = (turn.content or "").strip()[:200] or None
        messages.append(_assistant_message(turn))

        if not turn.tool_calls:
            trace(step, "nudge", summary="模型未调用工具，已提醒继续", model_note=note)
            messages.append({"role": "user", "content": NUDGE})
            continue

        finish_calls = [tc for tc in turn.tool_calls if tc.name == "finish"]
        others = [tc for tc in turn.tool_calls if tc.name != "finish"]
        limit_hit = False

        for i, tc in enumerate(others):
            if tool_calls_used >= config.max_tool_calls:
                for skipped in others[i:] + finish_calls:
                    messages.append(_tool_message(skipped, err("skipped", "limit_reached")))
                    trace(step, "skipped", tool=skipped.name, ok=False, summary="已达工具调用上限，未执行",
                          error_code="skipped")
                limit_hit = True
                break
            tool_calls_used += 1
            args, parse_error = _parse_args(tc.arguments)
            reason = str(args.pop("reason", "") or "") if args is not None else ""
            if parse_error:
                result = err("invalid_arguments", parse_error)
            elif tc.name not in TOOL_NAMES:
                result = err("unknown_tool", f"不存在工具 {tc.name}")
            else:
                result = toolbox.execute(tc.name, args, step)
            messages.append(_tool_message(tc, result))
            trace(
                step,
                "tool",
                tool=tc.name,
                args=args,
                reason=reason,
                ok=result["ok"],
                summary=summarize(tc.name, args or {}, result),
                error_code=None if result["ok"] else result["error"]["code"],
                model_note=note if i == 0 else None,
            )
        if limit_hit:
            incomplete_reason = "max_tool_calls_exceeded"
            break
        if not finish_calls:
            continue

        if others or len(finish_calls) > 1:
            for tc in finish_calls:
                messages.append(_tool_message(tc, err("invalid_arguments", "finish 必须单独调用，请在其他工具结果返回后再调用")))
                trace(step, "finish_rejected", tool="finish", ok=False, summary="finish 未单独调用（不计入打回次数）",
                      error_code="invalid_arguments")
            continue

        tc = finish_calls[0]
        args, parse_error = _parse_args(tc.arguments)
        if parse_error:
            problems = [parse_error]
        else:
            problems = validate_args("finish", args)
            if not problems:
                problems = validate_finish(args["results"], request, session)
        if problems:
            rejections += 1
            messages.append(_tool_message(tc, {"ok": False, "error": {"code": "invalid_arguments", "message": "finish 校验未通过", "problems": problems}}))
            trace(step, "finish_rejected", tool="finish", args=args, ok=False,
                  summary=f"打回第 {rejections} 次: " + "；".join(problems)[:200],
                  error_code="invalid_arguments", model_note=note)
            if rejections > config.max_finish_rejections:
                incomplete_reason = "finish_rejected"
                break
            continue

        results = args["results"]
        messages.append(_tool_message(tc, {"ok": True, "data": {"accepted": True}}))
        decisions = "，".join(f"{r['material_id']}={r['decision']}" for r in results)
        trace(step, "finish", tool="finish", args=args, ok=True, summary=f"结论: {decisions}", model_note=note)
        break

    meta = {
        "run_status": "completed" if results is not None else "incomplete",
        "incomplete_reason": incomplete_reason,
        "error": error,
        "mode": config.mode,
        "model": config.model,
        "steps_used": steps_used,
        "tool_calls_used": tool_calls_used,
        "finish_rejections": rejections,
    }
    report = build_report(request, session, drafts, results, meta)
    config_dict = {
        "mode": config.mode,
        "model": config.model,
        "max_steps": config.max_steps,
        "max_tool_calls": config.max_tool_calls,
        "max_finish_rejections": config.max_finish_rejections,
        "fault": f"save={config.fault}" if config.fault else None,
        "schedule": Path(config.schedule_path).as_posix(),
        "state_dir": _display_path(config.state_dir),
    }
    return RunResult(report=report, steps=steps, config=config_dict, state_dir=config.state_dir, session=session)
