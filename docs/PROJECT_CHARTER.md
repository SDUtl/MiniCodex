# Mini Codex：Harness Engineering 学习项目章程

## 1. 项目使命

Mini Codex 的首要目标不是尽快做出功能丰富的 Coding Agent，也不是用成熟 Agent Framework 拼装一个可运行 Demo，而是：

> 通过亲手实现一个最小但完整的 Coding Agent Harness，系统理解 Harness Engineering 的核心概念、架构、设计权衡和工程实现。

项目优先级是：

```text
学习价值 > 开发速度 > 功能数量
```

前几个阶段优先使用 Python、LLM API、标准库和少量必要依赖。Agent Loop、Tool Runtime、Context、Planning、Memory 和 Checkpoint 等关键机制，优先自己实现最小版本，不交给高级 Agent Framework 隐藏。

## 2. 最终目标

最终实现一个能够在真实 Git Repository 中理解任务、搜索代码、修改代码、执行命令、消费执行结果、从失败中继续修复并验证结果的 Mini Codex。

目标运行链路：

```text
User Task
    ↓
Task Initialization
    ↓
Context Builder
    ↓
Agent Loop
    ↓
LLM Reasoning
    ↓
Tool Selection
    ↓
Tool Execution
    ↓
Observation
    ↓
State Update
    ↓
Context Management
    ↓
Planning / Todo
    ↓
Verification
    ↓
Continue / Finish
```

后续再加入 Checkpoint / Resume、Sandbox、Permission、Tracing、Evaluation 和 Subagent。

## 3. 核心学习问题

完成项目后，应当能够从第一性原理回答：

1. Agent Loop 的本质是什么？
2. LLM 如何通过 Tool Calling 与真实环境交互？
3. Agent 如何读取和修改真实代码仓库？
4. Tool Runtime 应如何设计？
5. Context Window 应放什么、不应放什么？
6. Coding Agent 如何寻找与任务相关的代码？
7. Context 太长时如何 Compaction？
8. Agent 为什么需要 State？
9. Planning / Todo 什么时候有帮助，什么时候增加复杂度？
10. Agent 如何判断任务是否真正完成？
11. Tool 执行失败后如何恢复？
12. 长时间运行的 Agent 如何 Checkpoint / Resume？
13. Coding Agent 为什么需要 Sandbox？
14. Permission System 应如何设计？
15. 如何记录完整 Agent Trace？
16. 如何评价 Agent 是否真的完成任务？
17. Agent Harness 和 Evaluation Harness 有什么区别？
18. Subagent 应解决什么问题？
19. Harness 如何影响同一个模型的最终表现？
20. Codex、Claude Code、OpenHands 和 SWE-agent 一类系统的 Harness 大致如何工作？

## 4. 开发与学习方法

### 4.1 逐阶段演进

项目严格按照 V0 → V8 推进。当前阶段未验收、未完成学习复盘前，不主动实现后续阶段。

### 4.2 小需求检查点

每个阶段继续拆成可运行、可验证的小需求。每完成一个小需求：

1. 展示代码和验证证据；
2. 解释 Why / Without It / How；
3. 进行一次加入机制前后的对照；
4. 说明实现边界和 trade-off；
5. 停止开发，等待学习者确认后再继续。

### 4.3 失败驱动学习

重要机制应尽可能配套一个 failure case：先看到缺失机制导致的具体失败，再加入最小实现观察变化。

### 4.4 保持实现透明

代码应让学习者能直接看到：

```text
Agent 如何循环
Context 如何构造
Tool 如何执行
Observation 如何回填
State 如何变化
任务如何验证
```

不为“企业级架构”提前引入 interface、factory、dependency injection 或多层抽象。只有当前问题确实需要时才增加边界。

## 5. 阶段路线

### V0：最小 Agent Loop

实现 LLM 调用、Tool Calling、消息历史、工具结果回填和最小 `while` 循环。只提供 `read_file` 和 `shell`，目标是理解 Agent Loop，而不是完成真实 Bug 修复。

### V1：Coding Agent Tool Runtime

加入专用 `write_file` / `edit_file`、`grep`、`glob`、`git_diff`，研究 Tool Schema、分发、执行、Observation 和错误处理，使 Agent 可以操作真实 Git Repository。

### V2：Context Engineering

实现最小 Context Manager，研究任务、消息、工具结果、相关文件和仓库结构的选择与预算。

### V3：Planning + Agent State

加入 Task、Plan、Todo、Current Step 和 Completed Steps，研究任务分解、状态转换以及 Planning 的收益和成本。

### V4：Context Compaction

当消息、文件内容和命令输出超过预算时，组合 Summary、Important State 和 Recent Context，研究信息压缩和丢失。

### V5：Checkpoint + Resume

持久化 Task、Messages、State、Plan、Context Summary、Tool History 和 Workspace Metadata，使 Agent 能够在退出后恢复。

### V6：Sandbox + Permission

加入文件系统隔离、命令限制、超时、资源限制、网络控制和审批，研究 Coding Agent 的安全执行边界。

### V7：Tracing + Evaluation

记录 LLM 调用、工具调用、编辑、测试和最终结果，统计 token、延迟、迭代和错误；再通过测试、Diff 和轨迹实现最小 Evaluation Harness。

### V8：Subagent

最后研究 Explore、Test、Review 等有明确边界的委派任务，评估 Context Isolation、并行、协调成本和结果汇总。

## 6. 最终验收

最终命令形态：

```bash
mini-codex ./some-repository \
  "修复这个项目中的某个 bug，并确保所有测试通过"
```

Agent 应能够理解任务、检查仓库、建立上下文、制定计划、修改代码、运行测试、根据错误继续修改、检查 Git Diff 并验证结果，同时具备 Context、State、Compaction、Checkpoint、Sandbox、Permission、Tracing、Evaluation 和 Subagent 能力。

## 7. 最终学习成果

学习者应能够不依赖具体 Framework，画出并解释 Agent Harness 的完整数据流，并逐一说明 Context、Memory、Planning、Tool、Sandbox、Checkpoint、Permission、Trace、Eval 和 Subagent：

- 为什么存在；
- 解决什么问题；
- 如何实现最小版本；
- 有什么 trade-off；
- 工业级系统会如何继续演进。

项目不是为了重新制造商业版 Codex，而是以 Mini Codex 为实验载体，逐层建立对 Harness Engineering 的完整知识体系。
