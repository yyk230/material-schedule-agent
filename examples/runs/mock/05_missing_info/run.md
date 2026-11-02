# Run REQ-003

- mode: `mock`，model: `mock-rule-policy`
- run_status: `completed`
- steps_used: 11，tool_calls_used: 10，finish_rejections: 0
- config: `{"mode": "mock", "model": "mock-rule-policy", "max_steps": 20, "max_tool_calls": 40, "max_finish_rejections": 2, "fault": null, "schedule": "data/schedule.json", "state_dir": "<tempdir>"}`

> Mock 为规则策略，仅验证流程，不代表真实模型的决策效果。

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
| 1 | get_material | {"material_id": "M02"} | 先读取素材元数据 | 《城市夜跑 Vlog》；缺失 copyright_status | check_rules |
| 2 | check_rules | {"material_id": "M02"} | 检查审核规则与必填字段 | 风险 none；命中 R001；缺失 ['copyright_status'] | lookup_material_supplement |
| 3 | lookup_material_supplement | {"material_id": "M02", "fields": ["copyright_status"]} | 缺失 copyright_status，先补查 | 补查到 ['copyright_status']；仍缺 [] | check_rules |
| 4 | check_rules | {"material_id": "M02"} | 补查后重新检查规则 | 风险 none；命中 无；缺失 无 | query_slots |
| 5 | query_slots | {"material_id": "M02", "time": "14:00"} | 查询请求时间 14:00 是否可用 | 14:00 可用；可选 15:00/13:00/16:00 | save_schedule_draft |
| 6 | save_schedule_draft | {"material_id": "M02", "time": "14:00", "pending_confirmations": []} | 保存 14:00 的草稿 | 已保存 D-0001 14:00 (ready) | get_material |
| 7 | get_material | {"material_id": "M03"} | 先读取素材元数据 | 《周末露营装备清单》；缺失 owner | check_rules |
| 8 | check_rules | {"material_id": "M03"} | 检查审核规则与必填字段 | 风险 none；命中 R001；缺失 ['owner'] | lookup_material_supplement |
| 9 | lookup_material_supplement | {"material_id": "M03", "fields": ["owner"]} | 缺失 owner，先补查 | 补查到 []；仍缺 ['owner'] | check_rules |
| 10 | check_rules | {"material_id": "M03"} | 补查后重新检查规则 | 风险 none；命中 R001；缺失 ['owner'] | finish |
| 11 | finish | 见最终报告 |  | 结论: M02=approved，M03=info_missing | 结束：M02=approved，M03=info_missing |

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
  "mode": "mock",
  "model": "mock-rule-policy",
  "steps_used": 11,
  "tool_calls_used": 10,
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
      "reason": "无风险，请求时间可用；草稿已保存"
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
        "请补充字段: owner"
      ],
      "draft": {
        "status": "not_saved",
        "draft_id": null,
        "state": null,
        "error": null
      },
      "active_draft": null,
      "publish_status": "not_published",
      "reason": "补查后仍缺失 owner，不保存草稿"
    }
  ]
}
```
