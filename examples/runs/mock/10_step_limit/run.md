# Run REQ-003

- mode: `mock`，model: `mock-rule-policy`
- run_status: `incomplete`，原因: `max_steps_exceeded`
- steps_used: 2，tool_calls_used: 2，finish_rejections: 0
- config: `{"mode": "mock", "model": "mock-rule-policy", "max_steps": 2, "max_tool_calls": 40, "max_finish_rejections": 2, "fault": null, "schedule": "data/schedule.json", "state_dir": "<tempdir>"}`

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
| 2 | check_rules | {"material_id": "M02"} | 检查审核规则与必填字段 | 风险 none；命中 R001；缺失 ['copyright_status'] | 结束：incomplete（max_steps_exceeded） |

## 最终报告

- M02: incomplete | 风险 none | 请求 14:00 -> 建议 - | 草稿 not_saved | not_published
- M03: incomplete | 风险 None | 请求 15:00 -> 建议 - | 草稿 not_saved | not_published

summary: `{"incomplete": ["M02", "M03"], "blocked": [], "info_missing": [], "save_failed": [], "needs_confirmation": [], "ready": []}`

```json
{
  "run_status": "incomplete",
  "incomplete_reason": "max_steps_exceeded",
  "error": null,
  "request_id": "REQ-003",
  "mode": "mock",
  "model": "mock-rule-policy",
  "steps_used": 2,
  "tool_calls_used": 2,
  "finish_rejections": 0,
  "summary": {
    "incomplete": [
      "M02",
      "M03"
    ],
    "blocked": [],
    "info_missing": [],
    "save_failed": [],
    "needs_confirmation": [],
    "ready": []
  },
  "items": [
    {
      "material_id": "M02",
      "review_status": "incomplete",
      "risk_level": "none",
      "risk_reasons": [],
      "missing_fields": [
        "copyright_status"
      ],
      "requested_slot": {
        "channel": "douyin",
        "date": "2026-11-05",
        "time": "14:00"
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
      "reason": ""
    },
    {
      "material_id": "M03",
      "review_status": "incomplete",
      "risk_level": null,
      "risk_reasons": [],
      "missing_fields": [],
      "requested_slot": {
        "channel": "douyin",
        "date": "2026-11-05",
        "time": "15:00"
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
      "reason": ""
    }
  ]
}
```
