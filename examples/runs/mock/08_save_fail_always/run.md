# Run REQ-001

- mode: `mock`，model: `mock-rule-policy`
- run_status: `completed`
- steps_used: 6，tool_calls_used: 5，finish_rejections: 0
- config: `{"mode": "mock", "model": "mock-rule-policy", "max_steps": 20, "max_tool_calls": 40, "max_finish_rejections": 2, "fault": "save=always", "schedule": "data/schedule.json", "state_dir": "<tempdir>"}`

> Mock 为规则策略，仅验证流程，不代表真实模型的决策效果。

## 请求

```json
{
  "request_id": "REQ-001",
  "items": [
    {
      "material_id": "M06",
      "channel": "douyin",
      "date": "2026-11-05",
      "time": "10:00",
      "time_hard": false
    }
  ]
}
```

## 执行步骤

| 步骤 | 动作 | 参数 | 依据 | 返回摘要 | 后续动作 |
|---|---|---|---|---|---|
| 1 | get_material | {"material_id": "M06"} | 先读取素材元数据 | 《家常菜三分钟教程》；字段完整 | check_rules |
| 2 | check_rules | {"material_id": "M06"} | 检查审核规则与必填字段 | 风险 none；命中 无；缺失 无 | query_slots |
| 3 | query_slots | {"material_id": "M06", "time": "10:00"} | 查询请求时间 10:00 是否可用 | 10:00 可用；可选 11:00/09:00/08:00 | save_schedule_draft |
| 4 | save_schedule_draft | {"material_id": "M06", "time": "10:00", "pending_confirmations": []} | 保存 10:00 的草稿 | 保存失败: tool_unavailable - 草稿存储暂时不可用，本次未保存 | save_schedule_draft |
| 5 | save_schedule_draft | {"material_id": "M06", "time": "10:00", "pending_confirmations": []} | 保存 10:00 的草稿 | 保存失败: tool_unavailable - 草稿存储暂时不可用，本次未保存 | finish |
| 6 | finish | 见最终报告 |  | 结论: M06=approved | 结束：M06=approved |

## 最终报告

- M06: approved | 风险 none | 请求 10:00 -> 建议 10:00 | 草稿 failed (tool_unavailable) | not_published

summary: `{"incomplete": [], "blocked": [], "info_missing": [], "save_failed": ["M06"], "needs_confirmation": [], "ready": []}`

```json
{
  "run_status": "completed",
  "incomplete_reason": null,
  "error": null,
  "request_id": "REQ-001",
  "mode": "mock",
  "model": "mock-rule-policy",
  "steps_used": 6,
  "tool_calls_used": 5,
  "finish_rejections": 0,
  "summary": {
    "incomplete": [],
    "blocked": [],
    "info_missing": [],
    "save_failed": [
      "M06"
    ],
    "needs_confirmation": [],
    "ready": []
  },
  "items": [
    {
      "material_id": "M06",
      "review_status": "approved",
      "risk_level": "none",
      "risk_reasons": [],
      "missing_fields": [],
      "requested_slot": {
        "channel": "douyin",
        "date": "2026-11-05",
        "time": "10:00"
      },
      "suggested_slot": {
        "channel": "douyin",
        "date": "2026-11-05",
        "time": "10:00"
      },
      "slot_changed": false,
      "pending_confirmations": [],
      "draft": {
        "status": "failed",
        "draft_id": null,
        "state": null,
        "error": "tool_unavailable"
      },
      "active_draft": null,
      "publish_status": "not_published",
      "reason": "无风险，请求时间可用；草稿保存失败（tool_unavailable）"
    }
  ]
}
```
