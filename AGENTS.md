# Mini Codex 协作规则

## 项目定位

Mini Codex 是 Harness Engineering 学习项目，不是商业级 Coding Agent 复刻项目。

始终遵循：

```text
学习价值 > 开发速度 > 功能数量
可读性 > 抽象程度
```

## 阶段门禁

1. 严格按照 V0 → V8 推进。
2. 当前阶段没有完成并经学习者确认前，不实现后续阶段。
3. 每个阶段拆成小需求；每完成一个小需求，停止开发并进行学习复盘。
4. 只有学习者明确确认继续后，才能进入下一个小需求。
5. 不预先创建尚未产生真实需求的抽象、模块或目录。

## 机制讲解协议

实现重要 Harness 机制前必须说明：

- **Why**：为什么 Coding Agent 需要它？
- **Without It**：没有它会出现什么具体失败？
- **How**：当前阶段准备怎样实现最小版本？

实现后必须：

- 展示可复现的运行或测试证据；
- 解释关键数据如何流动、状态如何变化；
- 对比加入机制前后的行为；
- 说明当前实现的边界和 trade-off；
- 等待学习者确认吸收后再继续。

## 当前范围

当前阶段是 V0：最小 Agent Loop。V0 只允许实现：

- 单次 LLM 调用；
- `read_file`；
- `shell`；
- Tool Calling 请求、执行和结果回填；
- `while` 循环、消息历史和最小终止条件；
- 支撑上述行为的必要测试和 CLI。

V0 不实现 Tool Registry 抽象、专用编辑工具、Context Manager、Planning、持久化 State、Compaction、Checkpoint、Sandbox、Permission、Tracing、Evaluation 或 Subagent。

完整目标和阶段定义见 `docs/PROJECT_CHARTER.md`，当前阶段设计见 `docs/stages/V0_AGENT_LOOP.md`。
