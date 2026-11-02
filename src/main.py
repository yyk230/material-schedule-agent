from __future__ import annotations

import argparse
import os
import sys
import tempfile
from typing import Any

from dotenv import load_dotenv

from .agent import RunResult, run_once
from .faults import parse_fault
from .models import DATE_RE, TIME_RE, Request, RequestItem, RunConfig
from .store import Dataset, read_json
from .trace import item_line, write_outputs


class RequestError(ValueError):
    pass


def parse_request(raw: Any, dataset: Dataset) -> Request:
    """校验请求文件；素材是否存在不在此校验，交给 Agent 走 not_found 分支。"""
    if not isinstance(raw, dict) or not str(raw.get("request_id") or "").strip():
        raise RequestError("request_id 不能为空")
    items_raw = raw.get("items")
    if not isinstance(items_raw, list) or not items_raw:
        raise RequestError("items 必须是非空数组")
    items, seen = [], set()
    slots = dataset.slot_times
    for i, it in enumerate(items_raw):
        where = f"items[{i}]"
        try:
            item = RequestItem(
                material_id=str(it["material_id"]),
                channel=str(it["channel"]),
                date=str(it["date"]),
                time=str(it["time"]),
                time_hard=bool(it.get("time_hard", False)),
            )
        except (KeyError, TypeError) as e:
            raise RequestError(f"{where} 缺少字段: {e}") from None
        if item.material_id in seen:
            raise RequestError(f"{where} material_id 重复: {item.material_id}")
        seen.add(item.material_id)
        if item.channel not in dataset.channels:
            raise RequestError(f"{where} channel 不在 {dataset.channels} 中")
        if not DATE_RE.match(item.date):
            raise RequestError(f"{where} date 必须为 YYYY-MM-DD")
        if not TIME_RE.match(item.time) or item.time not in slots:
            raise RequestError(f"{where} time 必须是 {slots[0]}-{slots[-1]} 之间的整点")
        items.append(item)
    return Request(request_id=str(raw["request_id"]), items=items)


def build_llm(mock: bool, request: Request):
    if mock:
        from .mock_llm import MockLLM

        return MockLLM(request)
    if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("MODEL_NAME"):
        raise RequestError("未配置 OPENAI_API_KEY 或 MODEL_NAME（见 .env.example），或使用 --mock 离线运行")
    from .llm import OpenAICompatLLM

    return OpenAICompatLLM.from_env()


def execute(
    request_path: str,
    *,
    mock: bool,
    schedule: str = "data/schedule.json",
    state_dir: str | None = None,
    fault: str | None = None,
    max_steps: int = 20,
    max_tool_calls: int = 40,
    out: str | None = None,
    data_dir: str = "data",
) -> tuple[Request, RunResult]:
    dataset = Dataset.load(data_dir, schedule)
    request = parse_request(read_json(request_path), dataset)
    llm = build_llm(mock, request)
    config = RunConfig(
        mode="mock" if mock else "live",
        model=llm.model,
        max_steps=max_steps,
        max_tool_calls=max_tool_calls,
        fault=parse_fault(fault),
        schedule_path=schedule,
        state_dir=state_dir or tempfile.mkdtemp(prefix="agent-state-"),
        data_dir=data_dir,
    )
    result = run_once(request, llm, config)
    if out:
        write_outputs(out, request, result)
    return request, result


def print_result(result: RunResult, out: str | None) -> None:
    report = result.report
    status = report["run_status"] + (f" ({report['incomplete_reason']})" if report["incomplete_reason"] else "")
    print(f"run_status: {status}  steps={report['steps_used']} tool_calls={report['tool_calls_used']}")
    if report["error"]:
        print(f"error: {report['error']}")
    print("summary:", {k: v for k, v in report["summary"].items() if v})
    for item in report["items"]:
        print("  " + item_line(item))
    if out:
        print(f"输出: {out}")


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    load_dotenv()
    p = argparse.ArgumentParser(description="素材审核与发布排期 Agent")
    p.add_argument("--request", required=True, help="请求 JSON 路径")
    p.add_argument("--mock", action="store_true", help="使用离线 Mock 规则策略（不调用模型）")
    p.add_argument("--schedule", default="data/schedule.json")
    p.add_argument("--state-dir", default=None, help="草稿存储目录；缺省为新的临时目录")
    p.add_argument("--fault", default=None, help="故障注入：save=once 或 save=always")
    p.add_argument("--max-steps", type=int, default=20)
    p.add_argument("--max-tool-calls", type=int, default=40)
    p.add_argument("--out", default=None, help="输出目录（run.json / run.md / drafts.json）")
    a = p.parse_args(argv)
    try:
        _, result = execute(
            a.request,
            mock=a.mock,
            schedule=a.schedule,
            state_dir=a.state_dir,
            fault=a.fault,
            max_steps=a.max_steps,
            max_tool_calls=a.max_tool_calls,
            out=a.out,
        )
    except (RequestError, ValueError, FileNotFoundError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    print_result(result, a.out)
    return 0 if result.report["run_status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
