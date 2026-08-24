# Mini Codex

Mini Codex 是一个以学习 Harness Engineering 为第一目标的 Coding Agent 实验项目。

项目不会一次性实现完整 Agent，而是从最小 Agent Loop 开始，逐阶段加入工具运行时、Context、State、Compaction、Checkpoint、Sandbox、Evaluation 和 Subagent。每个机制都要先观察“没有它时会怎样”，再实现最小版本。

## 当前阶段

当前处于 **V0：最小 Agent Loop**。V0.1 至 V0.4 已确认；V0.5 的 `shell` 与失败 Observation 设计已确认，代码尚未开始实现。

- [长期项目章程](docs/PROJECT_CHARTER.md)
- [V0 设计与学习检查点](docs/stages/V0_AGENT_LOOP.md)

## 核心优先级

```text
学习价值 > 开发速度 > 功能数量
```

## V0.3 DeepSeek Smoke Test

先把 DeepSeek 密钥配置在本地 `.env`，再运行：

```bash
set -a
source .env
set +a
PYTHONPATH=src .venv/bin/python examples/v0_3_deepseek_smoke.py
```

这个脚本会真实调用 DeepSeek 两次，并打印第一次模型生成的 Tool Call、
`tool_call_id`、Harness 回填的文件内容和第二次模型生成的最终回答。脚本不会打印密钥。

对应的自动化测试使用 Fake Client，不消耗 API 额度：

```bash
PYTHONPATH=src .venv/bin/python -m unittest -v tests/test_v0_3_smoke.py
```
