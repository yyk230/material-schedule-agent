from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.faults import SaveFault
from src.models import Request, RequestItem
from src.store import Dataset, DraftStore, Session
from src.tools import ToolBox

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SCHEDULE = DATA / "schedule.json"
SCHEDULE_ALT = DATA / "schedule_alt.json"
INPUTS = ROOT / "examples" / "inputs"


def make_request(*items: tuple, request_id: str = "REQ-T") -> Request:
    """items: (material_id, time) 或 (material_id, time, time_hard)，渠道/日期固定为 douyin 2026-11-05。"""
    return Request(
        request_id=request_id,
        items=[
            RequestItem(material_id=i[0], channel="douyin", date="2026-11-05", time=i[1],
                        time_hard=i[2] if len(i) > 2 else False)
            for i in items
        ],
    )


def load_request(name: str) -> Request:
    raw = json.loads((INPUTS / name).read_text(encoding="utf-8"))
    return Request(raw["request_id"], [RequestItem(**it) for it in raw["items"]])


@pytest.fixture
def tmp_state(tmp_path: Path) -> str:
    return str(tmp_path / "state")


@pytest.fixture
def make_box(tmp_state):
    def _make(request: Request, schedule: Path = SCHEDULE, fault: str | None = None, state_dir: str | None = None):
        ds = Dataset.load(DATA, schedule)
        return ToolBox(ds, request, Session(), DraftStore(state_dir or tmp_state), SaveFault(fault))

    return _make
