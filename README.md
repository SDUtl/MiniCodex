# Mini Codex

Mini Codex 是一个以学习 Harness Engineering 为第一目标的 Coding Agent 实验项目。

项目不会一次性实现完整 Agent，而是从最小 Agent Loop 开始，逐阶段加入工具运行时、Context、State、Compaction、Checkpoint、Sandbox、Evaluation 和 Subagent。每个机制都要先观察“没有它时会怎样”，再实现最小版本。

## 当前阶段

当前处于 **V0：最小 Agent Loop**。V0.1 已确认；V0.2 `read_file` Schema 与直接执行已经实现并验证，正在等待学习确认。V0.3 尚未开始。

- [长期项目章程](docs/PROJECT_CHARTER.md)
- [V0 设计与学习检查点](docs/stages/V0_AGENT_LOOP.md)

## 核心优先级

```text
学习价值 > 开发速度 > 功能数量
```
