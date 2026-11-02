# Run REQ-005

- mode: `live`，model: `qwen3.8-omni-flash`
- run_status: `completed`
- steps_used: 4，tool_calls_used: 3，finish_rejections: 0
- config: `{"mode": "live", "model": "qwen3.8-omni-flash", "max_steps": 20, "max_tool_calls": 40, "max_finish_rejections": 2, "fault": null, "schedule": "data/schedule.json", "state_dir": "<tempdir>"}`

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
| 1 | get_material | {"material_id": "M07"} | 先读取素材 M07 元数据，了解字段完整性与内容信息 | 《新品发布会预告》；字段完整 | check_rules |
| 2 | check_rules | {"material_id": "M07"} | 对 M07 执行审核规则检查，确认风险等级与缺失字段 | 风险 none；命中 无；缺失 无 | query_slots |
| 3 | query_slots | {"material_id": "M07", "time": "18:00"} | M07 无风险且字段完整，查询 douyin 2026-11-05 18:00 是否可用 | 18:00 被 X90 占用；可选 19:00/17:00/20:00 | finish |
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
  "mode": "live",
  "model": "qwen3.8-omni-flash",
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
        "请求时段 douyin 2026-11-05 18:00 已被素材 X90 占用；M07 的 time_hard=true，未获授权改期，因此本次未保存任何草稿",
        "若可放宽时间硬性要求，同日同渠道可选替代时段为 19:00 / 17:00 / 20:00，请确认选择哪一个（或指定其他时段）后再排期",
        "若 18:00 为不可妥协的硬性要求，请先协调或释放 X90 在该时段的占用，再重新提交 M07 排期"
      ],
      "draft": {
        "status": "not_saved",
        "draft_id": null,
        "state": null,
        "error": null
      },
      "active_draft": null,
      "publish_status": "not_published",
      "reason": "M07（新品发布会预告，品牌类，版权 authorized，负责人 孙八）字段完整、规则检查无风险（risk_level=none）；但请求时段 18:00 被 X90 占用，且该素材 time_hard=true 不允许改期，故按硬性边界不保存草稿，仅给出结论与可选时段供用户决策。"
    }
  ]
}
```
