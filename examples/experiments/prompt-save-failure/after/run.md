# Run REQ-001

- mode: `live`，model: `qwen3.8-omni-flash`
- run_status: `completed`
- steps_used: 6，tool_calls_used: 5，finish_rejections: 1
- config: `{"mode": "live", "model": "qwen3.8-omni-flash", "max_steps": 20, "max_tool_calls": 40, "max_finish_rejections": 2, "fault": "save=always", "schedule": "data/schedule.json", "state_dir": "<tempdir>"}`

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
| 1 | get_material | {"material_id": "M06"} | 先读取素材元数据，确认字段完整性与基本信息 | 《家常菜三分钟教程》；字段完整 | check_rules |
| 1 | check_rules | {"material_id": "M06"} | 对素材做审核规则检查，确认风险等级与缺失字段 | 风险 none；命中 无；缺失 无 | query_slots |
| 2 | query_slots | {"material_id": "M06", "time": "10:00"} | 素材无风险且字段完整，查询请求的 10:00 时段是否可用 | 10:00 可用；可选 11:00/09:00/08:00 | save_schedule_draft |
| 3 | save_schedule_draft | {"material_id": "M06", "time": "10:00", "pending_confirmations": []} | 规则检查无风险、字段完整且 10:00 可用，按请求时间保存排期草稿 | 保存失败: tool_unavailable - 草稿存储暂时不可用，本次未保存 | save_schedule_draft |
| 4 | save_schedule_draft | {"material_id": "M06", "pending_confirmations": [], "time": "10:00"} | 上次保存返回 tool_unavailable，按规则重试一次保存 10:00 草稿 | 保存失败: tool_unavailable - 草稿存储暂时不可用，本次未保存 | finish |
| 5 | finish (finish_rejected) | 见最终报告 |  | 打回第 1 次: 参数 results 类型或取值不合法 | finish |
| 6 | finish | 见最终报告 |  | 结论: M06=needs_confirmation | 结束：M06=needs_confirmation |

## 最终报告

- M06: needs_confirmation | 风险 none | 请求 10:00 -> 建议 10:00 | 草稿 failed (tool_unavailable) | not_published

summary: `{"incomplete": [], "blocked": [], "info_missing": [], "save_failed": ["M06"], "needs_confirmation": [], "ready": []}`

```json
{
  "run_status": "completed",
  "incomplete_reason": null,
  "error": null,
  "request_id": "REQ-001",
  "mode": "live",
  "model": "qwen3.8-omni-flash",
  "steps_used": 6,
  "tool_calls_used": 5,
  "finish_rejections": 1,
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
      "review_status": "needs_confirmation",
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
      "pending_confirmations": [
        "草稿未落库：两次调用 save_schedule_draft 均返回 tool_unavailable（草稿存储暂时不可用），需稍后重试保存 2026-11-05 douyin 10:00 的排期，或改由人工录入",
        "素材审核无风险、字段完整，请求时段 10:00 查询结果为可用（同日同渠道备选 11:00 / 09:00 / 08:00），请确认是否维持原时段"
      ],
      "draft": {
        "status": "failed",
        "draft_id": null,
        "state": null,
        "error": "tool_unavailable"
      },
      "active_draft": null,
      "publish_status": "not_published",
      "reason": "M06 规则检查无风险且字段完整，10:00 时段可用，但草稿保存两次均因存储不可用失败，故结论为待确认，建议时间仍为 10:00。"
    }
  ]
}
```
