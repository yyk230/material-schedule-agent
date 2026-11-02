# Run REQ-004

- mode: `mock`，model: `mock-rule-policy`
- run_status: `completed`
- steps_used: 9，tool_calls_used: 8，finish_rejections: 0
- config: `{"mode": "mock", "model": "mock-rule-policy", "max_steps": 20, "max_tool_calls": 40, "max_finish_rejections": 2, "fault": null, "schedule": "data/schedule.json", "state_dir": "<tempdir>"}`

> Mock 为规则策略，仅验证流程，不代表真实模型的决策效果。

## 请求

```json
{
  "request_id": "REQ-004",
  "items": [
    {
      "material_id": "M04",
      "channel": "douyin",
      "date": "2026-11-05",
      "time": "16:00",
      "time_hard": false
    },
    {
      "material_id": "M05",
      "channel": "douyin",
      "date": "2026-11-05",
      "time": "11:00",
      "time_hard": false
    },
    {
      "material_id": "M08",
      "channel": "douyin",
      "date": "2026-11-05",
      "time": "09:00",
      "time_hard": false
    }
  ]
}
```

## 执行步骤

| 步骤 | 动作 | 参数 | 依据 | 返回摘要 | 后续动作 |
|---|---|---|---|---|---|
| 1 | get_material | {"material_id": "M04"} | 先读取素材元数据 | 《全网最低价！双11囤货清单》；字段完整 | check_rules |
| 2 | check_rules | {"material_id": "M04"} | 检查审核规则与必填字段 | 风险 high；命中 R002；缺失 无 | get_material |
| 3 | get_material | {"material_id": "M05"} | 先读取素材元数据 | 《经典电影混剪合集》；字段完整 | check_rules |
| 4 | check_rules | {"material_id": "M05"} | 检查审核规则与必填字段 | 风险 medium；命中 R003；缺失 无 | query_slots |
| 5 | query_slots | {"material_id": "M05", "time": "11:00"} | 查询请求时间 11:00 是否可用 | 11:00 可用；可选 10:00/13:00/09:00 | save_schedule_draft |
| 6 | save_schedule_draft | {"material_id": "M05", "time": "11:00", "pending_confirmations": ["版权状态 pending，需确认授权"]} | 保存 11:00 的草稿（附待确认项） | 已保存 D-0001 11:00 (pending_confirmation) | get_material |
| 7 | get_material | {"material_id": "M08"} | 先读取素材元数据 | 《秋季护肤套装限时优惠》；字段完整 | check_rules |
| 8 | check_rules | {"material_id": "M08"} | 检查审核规则与必填字段 | 风险 high；命中 R004；缺失 无 | finish |
| 9 | finish | 见最终报告 |  | 结论: M04=blocked，M05=needs_confirmation，M08=blocked | 结束：M04=blocked，M05=needs_confirmation，M08=blocked |

## 最终报告

- M04: blocked | 风险 high | 请求 16:00 -> 建议 - | 草稿 not_saved | not_published
- M05: needs_confirmation | 风险 medium | 请求 11:00 -> 建议 11:00 | 草稿 saved D-0001 | not_published
- M08: blocked | 风险 high | 请求 09:00 -> 建议 - | 草稿 not_saved | not_published

summary: `{"incomplete": [], "blocked": ["M04", "M08"], "info_missing": [], "save_failed": [], "needs_confirmation": ["M05"], "ready": []}`

```json
{
  "run_status": "completed",
  "incomplete_reason": null,
  "error": null,
  "request_id": "REQ-004",
  "mode": "mock",
  "model": "mock-rule-policy",
  "steps_used": 9,
  "tool_calls_used": 8,
  "finish_rejections": 0,
  "summary": {
    "incomplete": [],
    "blocked": [
      "M04",
      "M08"
    ],
    "info_missing": [],
    "save_failed": [],
    "needs_confirmation": [
      "M05"
    ],
    "ready": []
  },
  "items": [
    {
      "material_id": "M04",
      "review_status": "blocked",
      "risk_level": "high",
      "risk_reasons": [
        "R002: 标题或摘要含禁用词: 最低"
      ],
      "missing_fields": [],
      "requested_slot": {
        "channel": "douyin",
        "date": "2026-11-05",
        "time": "16:00"
      },
      "suggested_slot": null,
      "slot_changed": false,
      "pending_confirmations": [],
      "draft": {
        "status": "not_saved",
        "draft_id": null,
        "state": null,
        "error": null
      },
      "active_draft": null,
      "publish_status": "not_published",
      "reason": "高风险，阻断：标题或摘要含禁用词: 最低"
    },
    {
      "material_id": "M05",
      "review_status": "needs_confirmation",
      "risk_level": "medium",
      "risk_reasons": [
        "R003: 版权状态为 pending，需确认授权"
      ],
      "missing_fields": [],
      "requested_slot": {
        "channel": "douyin",
        "date": "2026-11-05",
        "time": "11:00"
      },
      "suggested_slot": {
        "channel": "douyin",
        "date": "2026-11-05",
        "time": "11:00"
      },
      "slot_changed": false,
      "pending_confirmations": [
        "版权状态 pending，需确认授权"
      ],
      "draft": {
        "status": "saved",
        "draft_id": "D-0001",
        "state": "pending_confirmation",
        "error": null
      },
      "active_draft": {
        "draft_id": "D-0001",
        "time": "11:00",
        "state": "pending_confirmation"
      },
      "publish_status": "not_published",
      "reason": "存在待确认事项；草稿已保存"
    },
    {
      "material_id": "M08",
      "review_status": "blocked",
      "risk_level": "high",
      "risk_reasons": [
        "R004: 广告类素材未带广告标识"
      ],
      "missing_fields": [],
      "requested_slot": {
        "channel": "douyin",
        "date": "2026-11-05",
        "time": "09:00"
      },
      "suggested_slot": null,
      "slot_changed": false,
      "pending_confirmations": [],
      "draft": {
        "status": "not_saved",
        "draft_id": null,
        "state": null,
        "error": null
      },
      "active_draft": null,
      "publish_status": "not_published",
      "reason": "高风险，阻断：广告类素材未带广告标识"
    }
  ]
}
```
