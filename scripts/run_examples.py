"""一键跑完运行矩阵（10 次运行），输出到 examples/runs/<mode>/<run_name>/。

用法: python scripts/run_examples.py --mode mock|live|both
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv  # noqa: E402

from src.main import execute, print_result  # noqa: E402

INPUTS = "examples/inputs"
CONFLICT_STATE = "conflict"  # 第 2、3、4 次运行共享

# (run_name, request, 额外参数, 共享 state 名或 None)
RUNS = [
    ("01_normal", "case01_normal.json", {}, None),
    ("02_conflict", "case02_conflict.json", {}, CONFLICT_STATE),
    ("03_duplicate", "case02_conflict.json", {}, CONFLICT_STATE),
    ("04_slot_changed", "case02_conflict.json", {"schedule": "data/schedule_alt.json"}, CONFLICT_STATE),
    ("05_missing_info", "case03_missing_info.json", {}, None),
    ("06_rule_risk", "case04_rule_risk.json", {}, None),
    ("07_hard_conflict", "case05_hard_conflict.json", {}, None),
    ("08_save_fail_always", "case01_normal.json", {"fault": "save=always"}, None),
    ("09_save_fail_once", "case01_normal.json", {"fault": "save=once"}, None),
    ("10_step_limit", "case03_missing_info.json", {"max_steps": 2}, None),
]


def run_mode(mode: str) -> int:
    runs_dir = Path("examples/runs") / mode
    state_root = Path(".state") / mode
    for d in (runs_dir, state_root):
        shutil.rmtree(d, ignore_errors=True)
    print(f"===== mode: {mode} =====")
    for name, req, extra, shared in RUNS:
        state_dir = str(state_root / shared) if shared else tempfile.mkdtemp(prefix="agent-state-")
        out = str(runs_dir / name)
        print(f"\n--- {name} ({req} {extra or ''}) ---")
        _, result = execute(f"{INPUTS}/{req}", mock=(mode == "mock"), state_dir=state_dir, out=out, **extra)
        print_result(result, out)
    return 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["mock", "live", "both"], default="mock")
    mode = p.parse_args().mode
    modes = ["mock", "live"] if mode == "both" else [mode]
    if "live" in modes and not (os.environ.get("OPENAI_API_KEY") and os.environ.get("MODEL_NAME")):
        print("错误: live 模式需要在 .env 中配置 OPENAI_API_KEY 与 MODEL_NAME", file=sys.stderr)
        return 1
    for m in modes:
        run_mode(m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
