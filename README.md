# 素材审核与发布排期 Agent

小影科技 2027 校招 AI Agent 笔试 · 项目题 1。

帮助内容团队审核待处理素材，并形成**无冲突、可确认**的发布排期草稿。Agent 只保存草稿，系统中不存在发布能力。

- 实现：Python 3.13 原生 ReAct 循环（未使用 Agent 框架），模型通过 OpenAI 兼容的 function calling 选择动作
- 运行方式：CLI
- 离线：`--mock` 使用规则策略 MockLLM，**只验证流程，不代表真实模型的决策效果**

## 环境与安装

```powershell
python -m venv .venv
.\.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

真实模型运行需要复制 `.env.example` 为 `.env` 并填写 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`MODEL_NAME`（需支持 function calling，建议非推理模型，如 `gpt-4o-mini` / `deepseek-chat` / `qwen-plus`）。离线 Mock 不需要任何配置。

## 运行

```powershell
# 离线 Mock（参考实例：M01 要求 18:00，已被占用）
python -m src.main --request examples/inputs/case02_conflict.json --mock

# 真实模型
python -m src.main --request examples/inputs/case02_conflict.json --out examples/runs/manual

# 一键跑完 10 次运行（输出到 examples/runs/<mode>/）
python scripts/run_examples.py --mode mock      # 或 live / both

# 测试（结果写入 examples/test-results.txt）
python scripts/run_tests.py
# 真实模型冒烟测试（默认不跑）
python -m pytest -m live
```

CLI 参数：

| 参数 | 说明 |
|---|---|
| `--request PATH` | 请求 JSON（见 `examples/inputs/`） |
| `--mock` | 离线规则策略 |
| `--schedule PATH` | 排期表，默认 `data/schedule.json` |
| `--state-dir DIR` | 草稿存储目录；缺省为新的临时目录（重复提交测试需显式共用） |
| `--fault save=once\|always` | 保存工具故障注入 |
| `--max-steps N` / `--max-tool-calls N` | 模型调用步数 / 工具调用次数上限，默认 20 / 40 |
| `--out DIR` | 输出 `run.json`、`run.md`、`drafts.json` |

退出码：`0` 完成，`2` 未完成（达到上限等），`1` 参数或配置错误。

## 评审入口

| 验收点 / 审核要点 | 运行 | 文件 |
|---|---|---|
| 正常排期 | 01_normal | `examples/runs/<mode>/01_normal/run.md` |
| 时段冲突（参考实例 19:00 待确认，不称已发布） | 02_conflict | `examples/runs/<mode>/02_conflict/run.md` |
| 重复提交只产生一份草稿 | 03_duplicate | `examples/runs/<mode>/03_duplicate/drafts.json` |
| 更换占用时段并重复提交 | 04_slot_changed | `examples/runs/<mode>/04_slot_changed/{run.md,drafts.json}` |
| 素材信息缺失（补查成功 / 失败） | 05_missing_info | `examples/runs/<mode>/05_missing_info/run.md` |
| 规则风险（高风险阻断 / 中风险待确认） | 06_rule_risk | `examples/runs/<mode>/06_rule_risk/run.md` |
| 确认边界（硬性时间不擅改） | 07_hard_conflict | `examples/runs/<mode>/07_hard_conflict/run.md` |
| 保存失败须明确返回失败 | 08_save_fail_always | `examples/runs/<mode>/08_save_fail_always/run.md` |
| 工具失败后由模型决定重试 | 09_save_fail_once | `examples/runs/<mode>/09_save_fail_once/run.md` |
| 达到步数上限返回未完成 | 10_step_limit | `examples/runs/<mode>/10_step_limit/run.md` |
| 测试结果 | — | `examples/test-results.txt` |

`<mode>` 为 `mock`（离线规则策略）或 `live`（真实模型）。预期与实际结果对照见 [docs/03-evaluation.md](docs/03-evaluation.md)。

## 目录

```
src/
  main.py        CLI 与请求校验
  agent.py       ReAct 循环：模型选动作 -> 执行工具 -> 观察 -> 模型决定下一步/结束；步数与调用上限
  llm.py         OpenAI 兼容模型接入
  mock_llm.py    离线规则策略（只验证流程）
  tools.py       5 个业务工具 + finish 的 schema、参数校验与实现
  store.py       数据加载、会话账本、草稿存储（幂等、替换、原子写）
  guardrails.py  finish 校验（V1-V8）与以账本为准组装报告
  faults.py      保存故障注入
  prompts.py     system prompt
  trace.py       run.json / run.md 输出
data/            合成素材、补查源、审核规则、两套排期表
examples/        inputs/ 请求，runs/ 运行记录，test-results.txt
tests/           工具、防线、Mock 端到端、剧本化异常行为、live 冒烟
docs/            01 需求 · 02 方案 · 03 评估 · 04 AI 使用 · 05 复盘
scripts/         run_examples.py 运行矩阵，run_tests.py 测试并落盘
```
