# 03 评估

## 验证方式

1. **单元与集成测试**：`python scripts/run_tests.py`，结果见 [examples/test-results.txt](../examples/test-results.txt)（66 passed，1 个 live 用例默认跳过）。
   - `tests/test_tools.py`：补查叠加、规则等级、替代时间排序、草稿占用、保存 8 步校验的顺序、幂等与替换、故障注入
   - `tests/test_guardrails.py`：V1-V8 正反例、报告字段来自账本、汇总分组优先级
   - `tests/test_agent_mock.py`：Mock 端到端跑完下表 10 次运行并逐项断言
   - `tests/test_agent_scripted.py`：用剧本模拟真实模型的错误行为（保存失败后谎报成功、只回文本、并行调用超限、finish 与其他工具同轮、finish 连续不合法、非法 JSON 与未知工具、模型接口异常）
   - `tests/test_live.py`：真实模型冒烟（`pytest -m live`）
2. **运行记录**：`python scripts/run_examples.py --mode mock|live`，每次运行输出 `run.json`（请求、配置、步骤、报告）、`run.md`（步骤表：步骤 / 动作 / 参数 / 依据 / 返回摘要 / 后续动作）和 `drafts.json`（草稿存储快照）。

## 运行矩阵：预期与 Mock 实际结果

Mock 是规则策略，结果确定，**只证明循环、工具和防线可用，不证明真实模型的决策效果**。

| # | 运行 | 输入与参数 | 预期 | Mock 实际 | 记录 |
|---|---|---|---|---|---|
| 1 | normal | case01 | M06 approved 10:00，saved D-0001 ready | 一致（5 步 / 4 次工具） | [run.md](../examples/runs/mock/01_normal/run.md) |
| 2 | conflict | case02 | M01 needs_confirmation，建议 19:00，saved D-0001 pending_confirmation，not_published | 一致（5 / 4） | [run.md](../examples/runs/mock/02_conflict/run.md) |
| 3 | duplicate | case02，共用 state | 同上，draft duplicate D-0001，草稿文件 1 条 | 一致（5 / 4） | [drafts.json](../examples/runs/mock/03_duplicate/drafts.json) |
| 4 | slot_changed | case02，共用 state，`schedule_alt.json` | 建议 20:00，saved D-0002 替换 D-0001，有效草稿 1 份 | 一致（5 / 4） | [run.md](../examples/runs/mock/04_slot_changed/run.md)、[drafts.json](../examples/runs/mock/04_slot_changed/drafts.json) |
| 5 | missing_info | case03 | M02 补查后 approved 14:00 saved；M03 info_missing [owner] not_saved | 一致（11 / 10） | [run.md](../examples/runs/mock/05_missing_info/run.md) |
| 6 | rule_risk | case04 | M04 blocked（R002）not_saved；M05 needs_confirmation（R003）11:00 pending_confirmation | 一致（7 / 6） | [run.md](../examples/runs/mock/06_rule_risk/run.md) |
| 7 | hard_conflict | case05 | M07 needs_confirmation，不建议时间、不保存，待确认项含 19:00 | 一致（4 / 3） | [run.md](../examples/runs/mock/07_hard_conflict/run.md) |
| 8 | save_fail_always | case01，`--fault save=always` | approved，draft failed（tool_unavailable），保存 2 次，summary.save_failed | 一致（6 / 5） | [run.md](../examples/runs/mock/08_save_fail_always/run.md) |
| 9 | save_fail_once | case01，`--fault save=once` | 第 1 次 tool_unavailable，重试后 saved，summary.ready | 一致（6 / 5） | [run.md](../examples/runs/mock/09_save_fail_once/run.md) |
| 10 | step_limit | case03，`--max-steps 2` | incomplete（max_steps_exceeded），两个素材 incomplete | 一致（2 / 2） | [run.md](../examples/runs/mock/10_step_limit/run.md) |

## 真实模型运行（live）

- 模型：阿里云百炼 OpenAI 兼容接口，`qwen3.8-omni-flash`，`temperature=0`
- 命令：`python scripts/run_examples.py --mode live`，2026-11-02 一次性跑完 10 次（约 4 分钟），每个用例只跑一次，未挑选
- 模型经常在同一轮并行调用多个工具（如同时 `get_material` 与 `check_rules`），因此步数少于 Mock

| # | 运行 | 模型实际行为与结论 | 与预期差异 | 记录 |
|---|---|---|---|---|
| 1 | normal | 读取+检查 -> 查 10:00 可用 -> 按原时间保存 -> approved，saved D-0001 ready | 无 | [run.md](../examples/runs/live/01_normal/run.md) |
| 2 | conflict | 查到 18:00 被 X90 占用 -> 选 19:00 保存并附待确认项（另列 17:00/20:00 备选）-> needs_confirmation，pending_confirmation，not_published | 无 | [run.md](../examples/runs/live/02_conflict/run.md) |
| 3 | duplicate | 同样选 19:00 保存，工具返回命中已有草稿 -> draft duplicate D-0001；草稿文件 1 条 | 无（待确认项措辞与第 2 次不同，按幂等设计原地更新） | [run.md](../examples/runs/live/03_duplicate/run.md)、[drafts.json](../examples/runs/live/03_duplicate/drafts.json) |
| 4 | slot_changed | 替代列表变为 20:00/16:00/15:00 -> 选 20:00 保存，替换 D-0001 -> saved D-0002；有效草稿 1 份 | 无 | [run.md](../examples/runs/live/04_slot_changed/run.md)、[drafts.json](../examples/runs/live/04_slot_changed/drafts.json) |
| 5 | missing_info | 两素材均缺字段 -> 并行补查 -> M02 补到版权后重新 check_rules、查时段、保存 -> approved；M03 仍缺 owner -> 不查时段不保存 -> info_missing，待确认项要求补 owner | 无 | [run.md](../examples/runs/live/05_missing_info/run.md) |
| 6 | rule_risk | M04 命中 R002 高风险 -> 不查时段不保存 -> blocked；M05 中风险 -> 查 11:00 可用 -> 带“确认授权”待确认项保存 -> needs_confirmation | 无 | [run.md](../examples/runs/live/06_rule_risk/run.md) |
| 7 | hard_conflict | 查到硬性时间 18:00 被占 -> 不保存、不改时间，待确认项列出 19:00/17:00/20:00 及“协调释放 X90”两种选择 -> needs_confirmation | 无 | [run.md](../examples/runs/live/07_hard_conflict/run.md) |
| 8 | save_fail_always | 保存返回 tool_unavailable -> 模型自行重试 1 次仍失败 -> 结论 needs_confirmation、不给建议时间，待确认项说明“未能生成草稿、请确认稍后重试或人工录入”；draft failed（tool_unavailable），归入 save_failed | **审核结论不同**：Mock 判 approved（审核通过但保存失败），模型判 needs_confirmation（因无草稿落库而交给用户）。两者都满足“明确返回失败、不虚报成功”，`draft.status` 与 `summary.save_failed` 一致 | [run.md](../examples/runs/live/08_save_fail_always/run.md) |
| 9 | save_fail_once | 首次保存 tool_unavailable -> 模型判断为瞬时错误重试 -> saved D-0001 -> approved，理由中注明“首次失败、重试后成功” | 无 | [run.md](../examples/runs/live/09_save_fail_once/run.md) |
| 10 | step_limit | 2 步内并行完成读取与规则检查（4 次工具调用）后达到步数上限 -> incomplete（max_steps_exceeded） | 无 | [run.md](../examples/runs/live/10_step_limit/run.md) |

### 动态决策证据

同一个循环、同一份 system prompt，模型根据工具返回选择了不同的后续动作（均可在对应 `run.md` 的“依据”列看到模型给出的决策理由）：

| 工具返回 | 模型后续动作 | 运行 |
|---|---|---|
| `query_slots`：请求时间可用 | 直接按原时间保存，结论 approved | live 01 |
| `query_slots`：请求时间被占用，`time_hard=false` | 从 alternatives 选 19:00，附待确认项保存，结论 needs_confirmation | live 02 |
| `query_slots`：替代列表变化（19:00 也被占） | 改选 20:00，旧草稿被替换 | live 04 |
| `query_slots`：请求时间被占用，`time_hard=true` | 不保存、不改时间，把选择权交给用户 | live 07 |
| `check_rules`：缺失字段 | 调用补查；补查结果不同 -> M02 重新检查后继续排期，M03 停止并标记 info_missing | live 05 |
| `check_rules`：high / medium | high 直接阻断且不再查时段；medium 带确认项保存 | live 06 |
| `save_schedule_draft`：tool_unavailable | 重试；重试成功 -> approved（live 09），重试仍失败 -> 停止重试并交用户确认（live 08） | live 08 / 09 |

## 失败与已发现问题

- Mock 运行矩阵与测试首次运行即全部通过；一个 V8 测试用例的设计错误在运行前已修正（见 [04-ai-usage.md](04-ai-usage.md)）。
- live 10 次运行全部按预期完成，`finish_rejections` 均为 0，也没有保存被业务校验拒绝。这说明本模型在这些用例中自行遵守了规则，但**也意味着工具层校验与 V1-V8 在 live 中没有被触发**，它们的有效性只由 `tests/test_tools.py`、`tests/test_guardrails.py`、`tests/test_agent_scripted.py` 证明。
- live 08 的审核结论与 Mock 不同（见上表），属于合理的策略差异，不是缺陷；但说明“保存失败时审核结论应如何给”在 prompt 中没有规定死，不同模型可能给出不同结论，报告以 `draft.status` 和 `summary.save_failed` 为准。
- 模型的文本说明（trace 中的 `model_note`）有时是英文，例如 “I'll start by reading the material metadata…”，不影响结论。
- live 结果只来自一个模型、每个用例一次，样本量小，不能代表其他模型或多次运行的稳定性。

## 已知限制

- **Mock 边界**：MockLLM 是固定规则策略，只验证流程与防线，不代表真实模型决策质量。
- **模型兼容性**：依赖 OpenAI 兼容的 function calling；推理模型或不支持 tools 的接口可能无法运行，或需要把 `LLM_TEMPERATURE` 留空。
- **没有确认回写**：待确认项只记录在草稿与报告中，用户确认后的回写（如把 `pending_confirmation` 改为 `ready`）未实现。
- **替代范围**：替代时间只在同日同渠道内查找，按整点小时划分时段。
- **存储**：JSON 文件存储，原子替换保证单进程不留半份文件，但不支持并发写。
- **V8 误判**：只识别紧邻的否定词，“不是已发布”这类写法会被误判为违规（prompt 已要求避免）。
- **live 随机性**：即使 `temperature=0`，不同模型或不同时间的结果也可能不同。
- **规则简化**：仅 3 条规则，禁用词为子串匹配，没有语义审核。
