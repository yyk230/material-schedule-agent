# Run REQ-001

- mode: `live`，model: `qwen3.8-omni-flash`
- run_status: `completed`
- steps_used: 5，tool_calls_used: 5，finish_rejections: 0
- config: `{"mode": "live", "model": "qwen3.8-omni-flash", "max_steps": 20, "max_tool_calls": 40, "max_finish_rejections": 2, "fault": "save=once", "schedule": "data/schedule.json", "state_dir": "<tempdir>"}`

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
| 1 | get_material | {"material_id": "M06"} | 先读取 M06 素材元数据，了解字段完整性与请求时间属性 | 《家常菜三分钟教程》；字段完整 | check_rules |
| 1 | check_rules | {"material_id": "M06"} | 对 M06 做审核规则检查，确认风险等级与缺失字段 | 风险 none；命中 无；缺失 无 | query_slots |
| 2 | query_slots | {"material_id": "M06", "time": "10:00"} | M06 无风险且字段完整，查询 douyin 2026-11-05 10:00 是否可用 | 10:00 可用；可选 11:00/09:00/08:00 | save_schedule_draft |
| 3 | save_schedule_draft | {"material_id": "M06", "time": "10:00", "pending_confirmations": []} | M06 字段完整、无风险，请求时间 10:00 可用，按原时间保存草稿 | 保存失败: tool_unavailable - 草稿存储暂时不可用，本次未保存 | save_schedule_draft |
| 4 | save_schedule_draft | {"material_id": "M06", "pending_confirmations": [], "time": "10:00"} | 上次保存因草稿存储暂时不可用失败，属瞬时错误，重试一次以完成排期 | 已保存 D-0001 10:00 (ready) | finish |
| 5 | finish | 见最终报告 | 模型说明: 草稿保存成功（D-0001）。现在提交结论。 | 结论: M06=approved | 结束：M06=approved |

## 最终报告

- M06: approved | 风险 none | 请求 10:00 -> 建议 10:00 | 草稿 saved D-0001 | not_published

summary: `{"incomplete": [], "blocked": [], "info_missing": [], "save_failed": [], "needs_confirmation": [], "ready": ["M06"]}`

```json
{
  "run_status": "completed",
  "incomplete_reason": null,
  "error": null,
  "request_id": "REQ-001",
  "mode": "live",
  "model": "qwen3.8-omni-flash",
  "steps_used": 5,
  "tool_calls_used": 5,
  "finish_rejections": 0,
  "summary": {
    "incomplete": [],
    "blocked": [],
    "info_missing": [],
    "save_failed": [],
    "needs_confirmation": [],
    "ready": [
      "M06"
    ]
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
        "status": "saved",
        "draft_id": "D-0001",
        "state": "ready",
        "error": null
      },
      "active_draft": {
        "draft_id": "D-0001",
        "time": "10:00",
        "state": "ready"
      },
      "publish_status": "not_published",
      "reason": "M06《家常菜三分钟教程》字段完整、版权 authorized，规则检查风险等级 none；douyin 2026-11-05 10:00 时段可用，已按请求时间保存排期草稿 D-0001（首次保存遇草稿存储瞬时不可用，重试后成功），无需额外确认项。注意：仅为草稿，尚未发布。"
    }
  ]
}
```
