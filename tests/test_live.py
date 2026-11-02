"""真实模型冒烟测试：默认不运行，使用 `pytest -m live` 手动执行（需要 .env）。"""

from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv

from src.main import execute
from tests.conftest import INPUTS, ROOT, SCHEDULE

load_dotenv(ROOT / ".env")

pytestmark = pytest.mark.live


@pytest.mark.skipif(not (os.environ.get("OPENAI_API_KEY") and os.environ.get("MODEL_NAME")), reason="未配置模型 API Key")
def test_live_conflict_case(tmp_state):
    _, result = execute(str(INPUTS / "case02_conflict.json"), mock=False, state_dir=tmp_state,
                        schedule=str(SCHEDULE), data_dir=str(ROOT / "data"))
    report = result.report
    assert report["run_status"] == "completed", report
    assert report["items"][0]["publish_status"] == "not_published"
