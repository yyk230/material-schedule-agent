# 01 需求

## 用户与目标

- **用户**：内容运营团队（排期负责人）。
- **目标**：对一批待排期素材完成审核，给出每项素材的审核状态、风险原因、建议时段、待确认项与草稿保存状态，形成**无冲突、可确认**的排期草稿。
- **边界**：只保存草稿，不接真实发布；未经用户同意不得擅自改变硬性发布要求。

## 输入

| 输入 | 位置 |
|---|---|
| 排期请求：素材 ID、渠道、日期、时间、时间是否硬性 | `examples/inputs/*.json` |
| 素材元数据 | `data/materials.json` |
| 补查资料源 | `data/material_supplements.json` |
| 审核规则 | `data/rules.json` |
| 已有排期 | `data/schedule.json`（`schedule_alt.json` 为更换占用后的版本） |

所有数据均为合成数据。

## 需求理解与取舍

1. **“找出待处理素材”**：请求给出需要排期的素材，最终报告由代码按 `blocked / info_missing / save_failed / needs_confirmation / ready` 分组（另有 `incomplete`），内容团队据此直接看到哪些素材需要人工处理、处理什么。未实现“扫描素材库自动发现待处理素材”。
2. **硬性发布要求**：渠道与日期始终视为硬性要求，工具不接受这两个参数；时间由请求字段 `time_hard` 决定，`true` 不可更改，`false`（默认）可改为同日同渠道的替代时间，但必须附待确认项，草稿状态为 `pending_confirmation`。
3. **请求确认**：没有交互式确认与回写流程。“请求确认”体现为草稿上的待确认项与结论 `needs_confirmation`，由内容团队线下确认。
4. **动态决策**：模型根据工具结果在补查、替代时段、请求确认、阻断、保存、重试、结束之间选择；代码只在写入前与结束时做校验，不替模型决定动作。

## 输出（每项素材）

`review_status`、`risk_level` / `risk_reasons` / `missing_fields`、`requested_slot` / `suggested_slot` / `slot_changed`、`pending_confirmations`、`draft`（saved / duplicate / failed / rejected / not_saved）、`active_draft`、`publish_status`（固定 `not_published`）、`reason`。

## 成功标准

每条对应 [03-evaluation.md](03-evaluation.md) 中的一次运行，Mock 模式下全部由 `tests/test_agent_mock.py` 自动断言。

| # | 场景 | 标准 |
|---|---|---|
| 1 | 正常排期 | 无风险、时段可用 -> `approved`，草稿 `ready` 已保存 |
| 2 | 时段冲突（参考实例） | M01 18:00 被占 -> 建议 19:00、`needs_confirmation`、草稿 `pending_confirmation`、`not_published` |
| 3 | 重复提交 | 相同请求再提交 -> 同一 `draft_id`，`duplicate`，草稿文件只有 1 条 |
| 4 | 更换占用时段并重复提交 | 19:00 也被占 -> 建议 20:00，新草稿替换旧草稿，有效草稿仍只有 1 份 |
| 5 | 素材信息缺失 | 补查成功则继续排期；补查失败 -> `info_missing`，不保存 |
| 6 | 规则风险 | 高风险 -> `blocked` 不保存；中风险 -> 带待确认项保存，`needs_confirmation` |
| 7 | 确认边界 | 硬性时间被占 -> 不改时间、不保存，列出可选时间待用户决定 |
| 8 | 保存失败 | 持续失败 -> `draft.status=failed` 并明确返回错误码，不虚报成功 |
| 9 | 工具失败后重试 | 一次失败 -> 是否重试由模型决定，trace 中可见 |
| 10 | 执行上限 | 达到步数上限 -> `run_status=incomplete` 并给出原因 |

非功能标准：离线可复现（Mock 结果确定）；真实密钥不入库；所有输出 UTF-8。
