from __future__ import annotations

from typing import Any

from .faults import SaveFault
from .models import DECISIONS, TIME_RE, Request, err, ok
from .store import Dataset, DraftStore, Session

REASON_PROP = {"type": "string", "description": "一句话说明为什么调用此工具（简要决策依据）"}


def _fn(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }


TOOL_SCHEMAS: list[dict[str, Any]] = [
    _fn(
        "get_material",
        "读取素材元数据（已合并补查结果），缺失字段为 null。",
        {"material_id": {"type": "string"}, "reason": REASON_PROP},
        ["material_id", "reason"],
    ),
    _fn(
        "lookup_material_supplement",
        "补查：从备用资料源查询素材缺失字段，查到的字段会合并进后续读取与规则检查。",
        {
            "material_id": {"type": "string"},
            "fields": {"type": "array", "items": {"type": "string"}, "description": "要补查的字段名"},
            "reason": REASON_PROP,
        },
        ["material_id", "fields", "reason"],
    ),
    _fn(
        "check_rules",
        "按审核规则检查素材，返回风险等级(none/medium/high)、缺失字段和命中规则"
        "（R001 缺失字段、R002 禁用词、R003 版权待确认、R004 广告未标识）。",
        {"material_id": {"type": "string"}, "reason": REASON_PROP},
        ["material_id", "reason"],
    ),
    _fn(
        "query_slots",
        "查询该素材请求渠道与日期下某个时间是否可用，并给出最近的空闲替代时间（同日同渠道，最多 3 个）。",
        {
            "material_id": {"type": "string"},
            "time": {"type": "string", "description": "HH:MM，整点"},
            "reason": REASON_PROP,
        },
        ["material_id", "time", "reason"],
    ),
    _fn(
        "save_schedule_draft",
        "保存排期草稿（仅草稿，不会发布）。渠道与日期取自请求。时间与请求不同或存在风险时必须附待确认项。"
        "同一素材同一时段重复保存只会更新原草稿。",
        {
            "material_id": {"type": "string"},
            "time": {"type": "string", "description": "HH:MM，整点"},
            "pending_confirmations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "需要用户确认的事项，无则传空数组",
            },
            "reason": REASON_PROP,
        },
        ["material_id", "time", "pending_confirmations", "reason"],
    ),
    _fn(
        "finish",
        "所有素材处理完毕后单独调用，提交每个素材的结论。",
        {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "material_id": {"type": "string"},
                        "decision": {"type": "string", "enum": list(DECISIONS)},
                        "suggested_time": {"type": "string", "description": "建议时间 HH:MM；不建议任何时段时传空串"},
                        "pending_confirmations": {"type": "array", "items": {"type": "string"}},
                        "reason": {"type": "string"},
                    },
                    "required": ["material_id", "decision", "suggested_time", "pending_confirmations", "reason"],
                },
            }
        },
        ["results"],
    ),
]

TOOL_NAMES = {s["function"]["name"] for s in TOOL_SCHEMAS}
_SCHEMA_BY_NAME = {s["function"]["name"]: s["function"]["parameters"] for s in TOOL_SCHEMAS}


def _type_ok(value: Any, schema: dict[str, Any]) -> bool:
    t = schema.get("type")
    if t == "string":
        return isinstance(value, str) and ("enum" not in schema or value in schema["enum"])
    if t == "array":
        return isinstance(value, list) and all(_type_ok(v, schema["items"]) for v in value)
    if t == "object":
        return isinstance(value, dict) and not _validate(value, schema)
    return True


def _validate(args: Any, schema: dict[str, Any]) -> list[str]:
    if not isinstance(args, dict):
        return ["参数必须是 JSON 对象"]
    problems = []
    for key in schema.get("required", []):
        if key == "reason":
            continue  # reason 缺失不报错，trace 记空串
        if key not in args:
            problems.append(f"缺少参数 {key}")
    for key, prop in schema.get("properties", {}).items():
        if key in args and not _type_ok(args[key], prop):
            problems.append(f"参数 {key} 类型或取值不合法")
    return problems


def validate_args(name: str, args: Any) -> list[str]:
    problems = _validate(args, _SCHEMA_BY_NAME[name])
    if not problems and "time" in args and not TIME_RE.match(args["time"]):
        problems.append("参数 time 必须为 HH:MM")
    return problems


def _time_diff(a: str, b: str) -> int:
    return abs(int(a[:2]) - int(b[:2]))


class ToolBox:
    def __init__(
        self,
        dataset: Dataset,
        request: Request,
        session: Session,
        drafts: DraftStore,
        fault: SaveFault | None = None,
    ):
        self.ds = dataset
        self.request = request
        self.session = session
        self.drafts = drafts
        self.fault = fault or SaveFault(None)

    # ---- 对外入口 ----
    def execute(self, name: str, args: dict[str, Any], step: int) -> dict[str, Any]:
        """执行业务工具（不含 finish）并记账。args 已剥离 reason。"""
        problems = validate_args(name, args)
        if problems:
            result = err("invalid_arguments", "；".join(problems))
        else:
            result = getattr(self, f"_t_{name}")(**args)
        self.session.record(step, name, args, result)
        return result

    # ---- 公共 ----
    def _merged(self, material_id: str) -> dict[str, Any] | None:
        base = self.ds.materials.get(material_id)
        if base is None:
            return None
        merged = dict(base)
        merged.update(self.session.overlay.get(material_id, {}))
        return merged

    def _occupied(self, channel: str, date: str, time: str, material_id: str) -> str | None:
        return self.ds.occupied_by(channel, date, time) or self.drafts.held_by_other(channel, date, time, material_id)

    def _not_in_request(self, material_id: str, code: str) -> dict[str, Any] | None:
        if self.request.item(material_id) is None:
            return err(code, f"素材 {material_id} 不在本次请求中")
        return None

    # ---- 工具实现 ----
    def _t_get_material(self, material_id: str) -> dict[str, Any]:
        if e := self._not_in_request(material_id, "not_found"):
            return e
        material = self._merged(material_id)
        if material is None:
            return err("not_found", f"素材库中不存在 {material_id}")
        return ok({"material": material})

    def _t_lookup_material_supplement(self, material_id: str, fields: list[str]) -> dict[str, Any]:
        if e := self._not_in_request(material_id, "invalid_arguments"):
            return e
        if material_id not in self.ds.materials:
            return err("not_found", f"素材库中不存在 {material_id}")
        source = self.ds.supplements.get(material_id, {})
        found = {f: source[f] for f in fields if source.get(f) not in (None, "")}
        still_missing = [f for f in fields if f not in found]
        if found:
            self.session.overlay.setdefault(material_id, {}).update(found)
        return ok({"found": found, "still_missing": still_missing})

    def _t_check_rules(self, material_id: str) -> dict[str, Any]:
        if e := self._not_in_request(material_id, "not_found"):
            return e
        m = self._merged(material_id)
        if m is None:
            return err("not_found", f"素材库中不存在 {material_id}")
        rules = self.ds.rules
        violations = []
        missing = [f for f in rules["required_fields"] if m.get(f) in (None, "")]
        if missing:
            violations.append({"rule_id": "R001", "detail": f"缺失字段: {', '.join(missing)}"})
        text = f"{m.get('title') or ''} {m.get('summary') or ''}"
        hits = [w for w in rules["banned_words"] if w in text]
        risk = "none"
        if hits:
            violations.append({"rule_id": "R002", "detail": f"标题或摘要含禁用词: {', '.join(hits)}"})
            risk = "high"
        if m.get("category") in rules.get("ad_categories", []) and m.get("ad_label") is not True:
            violations.append({"rule_id": "R004", "detail": f"{m.get('category')}类素材未带广告标识"})
            risk = "high"
        if m.get("copyright_status") == "pending":
            violations.append({"rule_id": "R003", "detail": "版权状态为 pending，需确认授权"})
            if risk == "none":
                risk = "medium"
        return ok({"risk_level": risk, "missing_fields": missing, "violations": violations})

    def _t_query_slots(self, material_id: str, time: str) -> dict[str, Any]:
        item = self.request.item(material_id)
        if item is None:
            return err("invalid_arguments", f"素材 {material_id} 不在本次请求中")
        slots = self.ds.slot_times
        if time not in slots:
            return err("slot_out_of_range", f"{time} 不在可排时段 {slots[0]}-{slots[-1]} 整点内")
        occupied_by = self._occupied(item.channel, item.date, time, material_id)
        free = [t for t in slots if t != time and not self._occupied(item.channel, item.date, t, material_id)]
        free.sort(key=lambda t: (_time_diff(t, time), -int(t[:2])))
        return ok(
            {
                "channel": item.channel,
                "date": item.date,
                "time": time,
                "requested_available": occupied_by is None,
                "occupied_by": occupied_by,
                "alternatives": free[:3],
            }
        )

    def _t_save_schedule_draft(self, material_id: str, time: str, pending_confirmations: list[str]) -> dict[str, Any]:
        item = self.request.item(material_id)
        if item is None:
            return err("invalid_arguments", f"素材 {material_id} 不在本次请求中")
        pending = [p.strip() for p in pending_confirmations if p and p.strip()]

        check = self.session.latest_check(material_id)
        if check is None:
            return err("precondition_failed", "本次会话尚未对该素材成功执行 check_rules")
        if check["missing_fields"]:
            return err("precondition_failed", f"最近一次规则检查仍缺失字段 {check['missing_fields']}，不能保存")
        if check["risk_level"] == "high":
            return err("precondition_failed", "最近一次规则检查为高风险，不能保存")

        slots = self.ds.slot_times
        if time not in slots:
            return err("slot_out_of_range", f"{time} 不在可排时段 {slots[0]}-{slots[-1]} 整点内")
        changed = time != item.time
        if item.time_hard and changed:
            return err("hard_constraint_violation", f"请求时间 {item.time} 为硬性要求，未经用户同意不得改为 {time}")
        if (check["risk_level"] == "medium" or changed) and not pending:
            reason = "存在中风险" if check["risk_level"] == "medium" else f"时间由 {item.time} 改为 {time}"
            return err("confirmation_required", f"{reason}，必须附待确认项")

        occupied_by = self._occupied(item.channel, item.date, time, material_id)
        if occupied_by:
            return err("slot_conflict", f"{item.channel} {item.date} {time} 已被 {occupied_by} 占用")
        if self.fault.should_fail():
            return err("tool_unavailable", "草稿存储暂时不可用，本次未保存")

        state = "pending_confirmation" if (pending or changed) else "ready"
        result = self.drafts.upsert(
            self.request.request_id, material_id, item.channel, item.date, time, state, pending
        )
        return ok({**result, "channel": item.channel, "date": item.date, "time": time})


def summarize(name: str, args: dict[str, Any], result: dict[str, Any]) -> str:
    """生成不超过 80 字的返回摘要，用于 trace。"""
    if not result.get("ok"):
        e = result["error"]
        prefix = "保存失败" if name == "save_schedule_draft" else "失败"
        return f"{prefix}: {e['code']} - {e['message']}"[:80]
    d = result["data"]
    if name == "get_material":
        m = d["material"]
        missing = [k for k, v in m.items() if v is None]
        return (f"《{m.get('title')}》" + (f"；缺失 {', '.join(missing)}" if missing else "；字段完整"))[:80]
    if name == "lookup_material_supplement":
        return f"补查到 {list(d['found'])}；仍缺 {d['still_missing']}"[:80]
    if name == "check_rules":
        rules = ",".join(v["rule_id"] for v in d["violations"]) or "无"
        return f"风险 {d['risk_level']}；命中 {rules}；缺失 {d['missing_fields'] or '无'}"[:80]
    if name == "query_slots":
        alts = "/".join(d["alternatives"]) or "无"
        state = "可用" if d["requested_available"] else f"被 {d['occupied_by']} 占用"
        return f"{d['time']} {state}；可选 {alts}"[:80]
    if name == "save_schedule_draft":
        tag = "命中已有草稿" if d["duplicate"] else "已保存"
        extra = f"；替换 {d['superseded']}" if d["superseded"] else ""
        return f"{tag} {d['draft_id']} {d['time']} ({d['state']}){extra}"[:80]
    return str(d)[:80]
