# Run REQ-002

- mode: `mock`，model: `mock-rule-policy`
- run_status: `completed`
- steps_used: 5，tool_calls_used: 4，finish_rejections: 0
- config: `{"mode": "mock", "model": "mock-rule-policy", "max_steps": 20, "max_tool_calls": 40, "max_finish_rejections": 2, "fault": null, "schedule": "data/schedule.json", "state_dir": ".state/mock/conflict"}`

> Mock 为规则策略，仅验证流程，不代表真实模型的决策效果。

## 请求

```json
{
  "request_id": "REQ-002",
  "items": [
    {
      "material_id": "M01",
      "channel": "douyin",
      "date": "2026-11-05",
      "time": "18:00",
      "time_hard": false
    }
  ]
}
```

## 执行步骤

| 步骤 | 动作 | 参数 | 依据 | 返回摘要 | 后续动作 |
|---|---|---|---|---|---|
| 1 | get_material | {"material_id": "M01"} | 先读取素材元数据 | 《秋季通勤穿搭指南》；字段完整 | check_rules |
| 2 | check_rules | {"material_id": "M01"} | 检查审核规则与必填字段 | 风险 none；命中 无；缺失 无 | query_slots |
| 3 | query_slots | {"material_id": "M01", "time": "18:00"} | 查询请求时间 18:00 是否可用 | 18:00 被 X90 占用；可选 19:00/17:00/20:00 | save_schedule_draft |
| 4 | save_schedule_draft | {"material_id": "M01", "time": "19:00", "pending_confirmations": ["18:00 已被 X90 占用，建议改为 19:00，需用户确认"]} | 保存 19:00 的草稿（附待确认项） | 命中已有草稿 D-0001 19:00 (pending_confirmation) | finish |
| 5 | finish | 见最终报告 |  | 结论: M01=needs_confirmation | 结束：M01=needs_confirmation |

## 最终报告

- M01: needs_confirmation | 风险 none | 请求 18:00 -> 建议 19:00 | 草稿 duplicate D-0001 | not_published

summary: `{"incomplete": [], "blocked": [], "info_missing": [], "save_failed": [], "needs_confirmation": ["M01"], "ready": []}`

```json
{
  "run_status": "completed",
  "incomplete_reason": null,
  "error": null,
  "request_id": "REQ-002",
  "mode": "mock",
  "model": "mock-rule-policy",
  "steps_used": 5,
  "tool_calls_used": 4,
  "finish_rejections": 0,
  "summary": {
    "incomplete": [],
    "blocked": [],
    "info_missing": [],
    "save_failed": [],
    "needs_confirmation": [
      "M01"
    ],
    "ready": []
  },
  "items": [
    {
      "material_id": "M01",
      "review_status": "needs_confirmation",
      "risk_level": "none",
      "risk_reasons": [],
      "missing_fields": [],
      "requested_slot": {
        "channel": "douyin",
        "date": "2026-11-05",
        "time": "18:00"
      },
      "suggested_slot": {
        "channel": "douyin",
        "date": "2026-11-05",
        "time": "19:00"
      },
      "slot_changed": true,
      "pending_confirmations": [
        "18:00 已被 X90 占用，建议改为 19:00，需用户确认"
      ],
      "draft": {
        "status": "duplicate",
        "draft_id": "D-0001",
        "state": "pending_confirmation",
        "error": null
      },
      "active_draft": {
        "draft_id": "D-0001",
        "time": "19:00",
        "state": "pending_confirmation"
      },
      "publish_status": "not_published",
      "reason": "存在待确认事项；草稿已保存"
    }
  ]
}
```
