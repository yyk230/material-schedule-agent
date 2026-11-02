# Run REQ-003

- mode: `live`，model: `qwen3.8-omni-flash`
- run_status: `completed`
- steps_used: 5，tool_calls_used: 9，finish_rejections: 0
- config: `{"mode": "live", "model": "qwen3.8-omni-flash", "max_steps": 20, "max_tool_calls": 40, "max_finish_rejections": 2, "fault": null, "schedule": "data/schedule.json", "state_dir": "<tempdir>"}`

## 请求

```json
{
  "request_id": "REQ-003",
  "items": [
    {
      "material_id": "M02",
      "channel": "douyin",
      "date": "2026-11-05",
      "time": "14:00",
      "time_hard": false
    },
    {
      "material_id": "M03",
      "channel": "douyin",
      "date": "2026-11-05",
      "time": "15:00",
      "time_hard": false
    }
  ]
}
```

## 执行步骤

| 步骤 | 动作 | 参数 | 依据 | 返回摘要 | 后续动作 |
|---|---|---|---|---|---|
| 1 | get_material | {"material_id": "M02"} | 读取 M02 素材元数据以了解字段完整性 | 《城市夜跑 Vlog》；缺失 copyright_status | get_material |
| 1 | get_material | {"material_id": "M03"} | 读取 M03 素材元数据以了解字段完整性 | 《周末露营装备清单》；缺失 owner | check_rules |
| 1 | check_rules | {"material_id": "M02"} | 按审核规则检查 M02 的风险与缺失字段 | 风险 none；命中 R001；缺失 ['copyright_status'] | check_rules |
| 1 | check_rules | {"material_id": "M03"} | 按审核规则检查 M03 的风险与缺失字段 | 风险 none；命中 R001；缺失 ['owner'] | lookup_material_supplement |
| 2 | lookup_material_supplement | {"material_id": "M02", "fields": ["copyright_status"]} | M02 缺失 copyright_status，需从备用资料源补查 | 补查到 ['copyright_status']；仍缺 [] | lookup_material_supplement |
| 2 | lookup_material_supplement | {"material_id": "M03", "fields": ["owner"]} | M03 缺失 owner，需从备用资料源补查 | 补查到 []；仍缺 ['owner'] | check_rules |
| 3 | check_rules | {"material_id": "M02"} | 补查 copyright_status 后需重新确认 M02 风险等级 | 风险 none；命中 无；缺失 无 | query_slots |
| 3 | query_slots | {"material_id": "M02", "time": "14:00"} | 确认 M02 请求的 14:00 时段是否可用 | 14:00 可用；可选 15:00/13:00/16:00 | save_schedule_draft |
| 4 | save_schedule_draft | {"material_id": "M02", "time": "14:00", "pending_confirmations": []} | M02 补查后字段完整、无风险且请求时段 14:00 可用，按原请求保存草稿 | 已保存 D-0001 14:00 (ready) | finish |
| 5 | finish | 见最终报告 |  | 结论: M02=approved，M03=info_missing | 结束：M02=approved，M03=info_missing |

## 最终报告

- M02: approved | 风险 none | 请求 14:00 -> 建议 14:00 | 草稿 saved D-0001 | not_published
- M03: info_missing | 风险 none | 请求 15:00 -> 建议 - | 草稿 not_saved | not_published

summary: `{"incomplete": [], "blocked": [], "info_missing": ["M03"], "save_failed": [], "needs_confirmation": [], "ready": ["M02"]}`

```json
{
  "run_status": "completed",
  "incomplete_reason": null,
  "error": null,
  "request_id": "REQ-003",
  "mode": "live",
  "model": "qwen3.8-omni-flash",
  "steps_used": 5,
  "tool_calls_used": 9,
  "finish_rejections": 0,
  "summary": {
    "incomplete": [],
    "blocked": [],
    "info_missing": [
      "M03"
    ],
    "save_failed": [],
    "needs_confirmation": [],
    "ready": [
      "M02"
    ]
  },
  "items": [
    {
      "material_id": "M02",
      "review_status": "approved",
      "risk_level": "none",
      "risk_reasons": [],
      "missing_fields": [],
      "requested_slot": {
        "channel": "douyin",
        "date": "2026-11-05",
        "time": "14:00"
      },
      "suggested_slot": {
        "channel": "douyin",
        "date": "2026-11-05",
        "time": "14:00"
      },
      "slot_changed": false,
      "pending_confirmations": [],
      "draft": {
        "status": "saved",
        "draft_id": "D-0001",
        "state": "ready",
        "error": null
      },
      "active_draft": {
        "draft_id": "D-0001",
        "time": "14:00",
        "state": "ready"
      },
      "publish_status": "not_published",
      "reason": "补查得到 copyright_status=authorized 后字段完整、规则检查无风险（risk none），请求时段 douyin/2026-11-05 14:00 可用，已成功保存排期草稿 D-0001（仅草稿，未发布）。"
    },
    {
      "material_id": "M03",
      "review_status": "info_missing",
      "risk_level": "none",
      "risk_reasons": [],
      "missing_fields": [
        "owner"
      ],
      "requested_slot": {
        "channel": "douyin",
        "date": "2026-11-05",
        "time": "15:00"
      },
      "suggested_slot": null,
      "slot_changed": false,
      "pending_confirmations": [
        "请提供 M03 的 owner（素材负责人）信息，缺失字段无法通过规则检查",
        "owner 补齐后需确认是否仍使用原请求时间 2026-11-05 15:00（douyin）再保存草稿"
      ],
      "draft": {
        "status": "not_saved",
        "draft_id": null,
        "state": null,
        "error": null
      },
      "active_draft": null,
      "publish_status": "not_published",
      "reason": "备用资料源仍未查到 owner 字段，补查后 check_rules 仍报缺失字段 owner（R001），信息不完整故不保存草稿。待确认：请补充 M03《周末露营装备清单》的素材负责人 owner，补齐后可按原请求 douyin/2026-11-05 15:00 重新排期（该时段当前未被本次 M02 草稿占用）。"
    }
  ]
}
```
