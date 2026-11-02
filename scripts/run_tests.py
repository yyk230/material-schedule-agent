"""运行 pytest 并把输出以 UTF-8 写入 examples/test-results.txt，透传 pytest 退出码。

用法: python scripts/run_tests.py [额外 pytest 参数]
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    cmd = [sys.executable, "-m", "pytest", "-v", "-p", "no:cacheprovider", *sys.argv[1:]]
    proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
    header = f"# {datetime.now().isoformat(timespec='seconds')}  $ {' '.join(['python', '-m', 'pytest', *cmd[3:]])}\n\n"
    output = header + proc.stdout + (proc.stderr or "")
    (ROOT / "examples" / "test-results.txt").write_text(output, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(output)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
