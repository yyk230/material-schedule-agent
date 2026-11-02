# Run REQ-005

- mode: `mock`，model: `mock-rule-policy`
- run_status: `completed`
- steps_used: 4，tool_calls_used: 3，finish_rejections: 0
- config: `{"mode": "mock", "model": "mock-rule-policy", "max_steps": 20, "max_tool_calls": 40, "max_finish_rejections": 2, "fault": null, "schedule": "data/schedule.json", "state_dir": "<tempdir>"}`

> Mock 为规则策略，仅验证流程，不代表真实模型的决策效果。

## 请求

```json
{
  "request_id": "REQ-005",
  "items": [
    {
      "material_id": "M07",
      "channel": "douyin",
      "date": "2026-11-05",
      "time": "18:00",
      "time_hard": true
    }
  ]
}
```

## 执行步骤

| 步骤 | 动作 | 参数 | 依据 | 返回摘要 | 后续动作 |
|---|---|---|---|---|---|
| 1 | get_material | {"material_id": "M07"} | 先读取素材元数据 | 《新品发布会预告》；字段完整 | check_rules |
| 2 | check_rules | {"material_id": "M07"} | 检查审核规则与必填字段 | 风险 none；命中 无；缺失 无 | query_slots |
| 3 | query_slots | {"material_id": "M07", "time": "18:00"} | 查询请求时间 18:00 是否可用 | 18:00 被 X90 占用；可选 19:00/17:00/20:00 | finish |
| 4 | finish | 见最终报告 |  | 结论: M07=needs_confirmation | 结束：M07=needs_confirmation |

## 最终报告

- M07: needs_confirmation | 风险 none | 请求 18:00 -> 建议 - | 草稿 not_saved | not_published

summary: `{"incomplete": [], "blocked": [], "info_missing": [], "save_failed": [], "needs_confirmation": ["M07"], "ready": []}`

```json
{
  "run_status": "completed",
  "incomplete_reason": null,
  "error": null,
  "request_id": "REQ-005",
  "mode": "mock",
  "model": "mock-rule-policy",
  "steps_used": 4,
  "tool_calls_used": 3,
  "finish_rejections": 0,
  "summary": {
    "incomplete": [],
    "blocked": [],
    "info_missing": [],
    "save_failed": [],
    "needs_confirmation": [
      "M07"
    ],
    "ready": []
  },
  "items": [
    {
      "material_id": "M07",
      "review_status": "needs_confirmation",
      "risk_level": "none",
      "risk_reasons": [],
      "missing_fields": [],
      "requested_slot": {
        "channel": "douyin",
        "date": "2026-11-05",
        "time": "18:00"
      },
      "suggested_slot": null,
      "slot_changed": false,
      "pending_confirmations": [
        "硬性时段 18:00 已被 X90 占用，可选 19:00/17:00/20:00，请用户决定"
      ],
      "draft": {
        "status": "not_saved",
        "draft_id": null,
        "state": null,
        "error": null
      },
      "active_draft": null,
      "publish_status": "not_published",
      "reason": "请求时间为硬性要求且已被占用，不擅自改时间，不保存草稿"
    }
  ]
}
```
