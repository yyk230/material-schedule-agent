# Run REQ-003

- mode: `live`，model: `qwen3.8-omni-flash`
- run_status: `completed`
- steps_used: 7，tool_calls_used: 10，finish_rejections: 0
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
| 1 | get_material | {"material_id": "M02"} | 读取 M02 素材元数据，判断字段完整性以进入规则检查 | 《城市夜跑 Vlog》；缺失 copyright_status | get_material |
| 1 | get_material | {"material_id": "M03"} | 读取 M03 素材元数据，判断字段完整性以进入规则检查 | 《周末露营装备清单》；缺失 owner | check_rules |
| 2 | check_rules | {"material_id": "M02"} | 检查 M02 是否存在缺失字段、禁用词、版权与广告标识风险 | 风险 none；命中 R001；缺失 ['copyright_status'] | check_rules |
| 2 | check_rules | {"material_id": "M03"} | 检查 M03 是否存在缺失字段、禁用词、版权与广告标识风险 | 风险 none；命中 R001；缺失 ['owner'] | lookup_material_supplement |
| 3 | lookup_material_supplement | {"material_id": "M02", "fields": ["copyright_status"]} | M02 缺失 copyright_status，先补查再重跑规则检查 | 补查到 ['copyright_status']；仍缺 [] | lookup_material_supplement |
| 3 | lookup_material_supplement | {"material_id": "M03", "fields": ["owner"]} | M03 缺失 owner，先补查再重跑规则检查 | 补查到 []；仍缺 ['owner'] | check_rules |
| 4 | check_rules | {"material_id": "M02"} | copyright_status 已补齐，重新检查确认风险等级 | 风险 none；命中 无；缺失 无 | query_slots |
| 5 | query_slots | {"material_id": "M02", "time": "14:00"} | M02 无风险且字段完整，确认请求时间 14:00 是否可用 | 14:00 可用；可选 15:00/13:00/16:00 | check_rules |
| 5 | check_rules | {"material_id": "M03"} | 补查后再次确认 M03 的缺失字段与风险等级 | 风险 none；命中 R001；缺失 ['owner'] | save_schedule_draft |
| 6 | save_schedule_draft | {"material_id": "M02", "time": "14:00", "pending_confirmations": []} | M02 字段完整、无风险且 14:00 可用，按请求时间保存草稿 | 已保存 D-0001 14:00 (ready) | finish |
| 7 | finish | 见最终报告 | 模型说明: M02 草稿已保存成功；M03 补查后仍缺 owner，按规则不保存草稿。现在提交结论。 | 结论: M02=approved，M03=info_missing | 结束：M02=approved，M03=info_missing |

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
  "steps_used": 7,
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
      "reason": "copyright_status 经补查为 authorized，字段完整、规则检查无风险（risk none），douyin 2026-11-05 14:00 时段可用，草稿已保存成功（draft_id D-0001，状态 ready）。仅为草稿，尚未发布。"
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
        "缺少 owner（素材归属人）字段，备用资料源未能补查到，需内容团队补充确认后再排期",
        "补充完成后需重新做规则检查并确认 douyin 2026-11-05 15:00 时段可用性，再保存草稿"
      ],
      "draft": {
        "status": "not_saved",
        "draft_id": null,
        "state": null,
        "error": null
      },
      "active_draft": null,
      "publish_status": "not_published",
      "reason": "素材存在且版权状态 authorized、规则检查风险为 none，但 owner 字段缺失且 lookup_material_supplement 补查后仍为 still_missing，按规则判定 info_missing，未保存任何草稿。"
    }
  ]
}
```
