from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


def read_json(path: str | Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str | Path, data: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


@dataclass
class Dataset:
    materials: dict[str, dict[str, Any]]
    supplements: dict[str, dict[str, Any]]
    rules: dict[str, Any]
    schedule: dict[str, Any]

    @classmethod
    def load(cls, data_dir: str | Path, schedule_path: str | Path) -> "Dataset":
        data_dir = Path(data_dir)
        materials = {m["id"]: m for m in read_json(data_dir / "materials.json")}
        return cls(
            materials=materials,
            supplements=read_json(data_dir / "material_supplements.json"),
            rules=read_json(data_dir / "rules.json"),
            schedule=read_json(schedule_path),
        )

    @property
    def channels(self) -> list[str]:
        return list(self.schedule["channels"])

    @property
    def slot_times(self) -> list[str]:
        start, end = self.schedule["slot_hours"]
        return [f"{h:02d}:00" for h in range(start, end + 1)]

    def occupied_by(self, channel: str, date: str, time: str) -> str | None:
        for o in self.schedule["occupied"]:
            if (o["channel"], o["date"], o["time"]) == (channel, date, time):
                return o["material_id"]
        return None


@dataclass
class Session:
    """单次运行的内存状态：补查叠加层与工具账本，不落盘。"""

    overlay: dict[str, dict[str, Any]] = field(default_factory=dict)
    ledger: list[dict[str, Any]] = field(default_factory=list)

    def record(self, step: int, tool: str, args: dict[str, Any], result: dict[str, Any]) -> None:
        entry = {"step": step, "tool": tool, "args": args, "ok": result["ok"]}
        entry.update({"data": result["data"]} if result["ok"] else {"error": result["error"]})
        self.ledger.append(entry)

    def entries(self, tool: str, material_id: str) -> list[dict[str, Any]]:
        return [e for e in self.ledger if e["tool"] == tool and e["args"].get("material_id") == material_id]

    def latest_check(self, material_id: str) -> dict[str, Any] | None:
        for e in reversed(self.entries("check_rules", material_id)):
            if e["ok"]:
                return e["data"]
        return None

    def last_save(self, material_id: str) -> dict[str, Any] | None:
        saves = self.entries("save_schedule_draft", material_id)
        return saves[-1] if saves else None

    def material_not_found(self, material_id: str) -> bool:
        return any(
            not e["ok"] and e["error"]["code"] == "not_found"
            for e in self.entries("get_material", material_id)
        )


class DraftStore:
    """草稿存储：<state_dir>/drafts.json，原子写，每个素材最多一份有效草稿。"""

    def __init__(self, state_dir: str | Path):
        self.path = Path(state_dir) / "drafts.json"

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"next_seq": 1, "drafts": []}
        return read_json(self.path)

    def _save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, self.path)

    def active(self, material_id: str) -> dict[str, Any] | None:
        for d in self.load()["drafts"]:
            if d["material_id"] == material_id and d["state"] != "superseded":
                return d
        return None

    def held_by_other(self, channel: str, date: str, time: str, material_id: str) -> str | None:
        for d in self.load()["drafts"]:
            if (
                d["state"] != "superseded"
                and d["material_id"] != material_id
                and (d["channel"], d["date"], d["time"]) == (channel, date, time)
            ):
                return d["material_id"]
        return None

    def upsert(
        self,
        request_id: str,
        material_id: str,
        channel: str,
        date: str,
        time: str,
        state: str,
        pending_confirmations: list[str],
    ) -> dict[str, Any]:
        data = self.load()
        now = datetime.now().isoformat(timespec="seconds")
        current = next(
            (d for d in data["drafts"] if d["material_id"] == material_id and d["state"] != "superseded"),
            None,
        )
        if current and (current["channel"], current["date"], current["time"]) == (channel, date, time):
            current.update(
                state=state,
                pending_confirmations=pending_confirmations,
                request_id=request_id,
                updated_at=now,
            )
            self._save(data)
            return {"draft_id": current["draft_id"], "duplicate": True, "state": state, "superseded": []}

        superseded = []
        if current:
            current.update(state="superseded", updated_at=now)
            superseded.append(current["draft_id"])
        draft_id = f"D-{data['next_seq']:04d}"
        data["next_seq"] += 1
        data["drafts"].append(
            {
                "draft_id": draft_id,
                "request_id": request_id,
                "material_id": material_id,
                "channel": channel,
                "date": date,
                "time": time,
                "state": state,
                "pending_confirmations": pending_confirmations,
                "created_at": now,
                "updated_at": now,
            }
        )
        self._save(data)
        return {"draft_id": draft_id, "duplicate": False, "state": state, "superseded": superseded}
