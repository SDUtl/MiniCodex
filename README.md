# Mini Codex

Mini Codex 是一个以学习 Harness Engineering 为第一目标的 Coding Agent 实验项目。

项目不会一次性实现完整 Agent，而是从最小 Agent Loop 开始，逐阶段加入工具运行时、Context、State、Compaction、Checkpoint、Sandbox、Evaluation 和 Subagent。每个机制都要先观察“没有它时会怎样”，再实现最小版本。

## 当前阶段

当前处于 **V0：最小 Agent Loop**。V0.1 至 V0.5 已确认；V0.6 的实现与技术验收已经完成，正在等待 V0 总学习复盘确认。

- [长期项目章程](docs/PROJECT_CHARTER.md)
- [V0 设计与学习检查点](docs/stages/V0_AGENT_LOOP.md)
- [V0 学习问题与参考答案](docs/stages/V0_REVIEW_QUESTIONS.md)

## 核心优先级

```text
学习价值 > 开发速度 > 功能数量
```

## V0 CLI

项目使用基于 `pyproject.toml` 的 Editable Install。先确保虚拟环境中的 pip 支持该安装方式：

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

在本地 `.env` 中配置 `DEEPSEEK_API_KEY` 后，由 Shell 导出环境变量并运行：

```bash
set -a
source .env
set +a

mini-codex . \
  "先读取 pyproject.toml，然后运行 PYTHONPATH=src python -m unittest -v，最后总结项目状态。"
```

Mini Codex 不会主动查找或加载 `.env`。

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
