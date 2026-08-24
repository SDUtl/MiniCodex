# V0：最小 Agent Loop

## 状态

- 总方向：已确认
- V0.0：已确认
- V0.1：已确认
- V0.2：已确认
- V0.3：实现与验证完成，等待学习者确认
- V0.4：尚未开始

## 1. 阶段目标

V0 只回答一个核心问题：

> LLM 如何通过 Harness 发出工具请求、获得真实环境的观察结果，并继续推理？

V0 不追求修复真实 Bug。它要产出一条透明、可测试、可逐步观察的最小闭环：

```text
User Task
    ↓
LLM Call
    ↓
Tool Call
    ↓
Harness Executes Tool
    ↓
Tool Result / Observation
    ↓
LLM Call
    ↓
Continue or Finish
```

## 2. Why / Without It / How

### Why

模型只能生成输出，不能自行读取本地文件或执行命令。Harness 必须负责解析模型的结构化工具请求、在环境中执行动作，并把结果作为新消息返回模型。重复这个过程，模型才可能根据真实观察调整下一步。

### Without It

只有一次模型调用时，模型可以建议“读取文件”或“运行测试”，但看不到结果，也无法根据错误继续处理。这只是单轮文本生成，不是 Agent。

### How

V0 使用一份持续追加的 `messages` 历史和一个直接可读的 `while` 循环：

1. 调用 LLM；
2. 保存模型回复；
3. 如果包含工具请求，则由 Harness 执行；
4. 将每个工具结果与对应的 tool call 关联后写回消息；
5. 再次调用 LLM；
6. 如果没有工具请求，则输出最终回复；
7. 达到最大轮数时停止。

## 3. 起步设计选择

采用“薄分层”而不是单文件或完整框架骨架：

```text
cli.py    接收仓库路径和任务
agent.py  保存消息并运行循环
llm.py    只负责一次模型 API 调用
tools.py  定义并执行 V0 的两个工具
```

不引入多供应商接口、Tool Registry、依赖注入、事件总线或持久化状态。V0 中 `messages` 就是最小的内存状态。

## 4. 小需求与学习检查点

### V0.0：固化项目章程与阶段契约

**需求**

- 保存长期项目目标、阶段边界和协作规则；
- 将 V0 拆成独立的小实验；
- 明确每个实验后必须暂停并等待学习确认。

**完成标准**

- `docs/PROJECT_CHARTER.md`、`AGENTS.md` 和本文档相互一致；
- 没有开始实现 Agent 代码；
- 学习者确认小需求划分后才进入 V0.1。

### V0.1：单次 LLM 调用——建立非 Agent 基线

**实现状态：完成，等待学习确认**

验证结果：

- 确定性测试证明请求只包含模型名和一条 user message；
- 真实 DeepSeek API 调用成功返回指定文本；
- 当被要求读取本地 `README.md` 时，模型明确表示无法访问本地文件；
- 当前实现没有工具、仓库 Context、消息历史或循环。

**本次只做**

- 接收一段用户文本；
- 调用一次 LLM；
- 输出模型的普通文本回复；
- 使用假客户端完成确定性测试，并进行一次真实 API smoke test。

**学习重点**

- 一次 LLM 请求包含什么输入，返回什么输出；
- 模型调用与 Agent Loop 的区别；
- 为什么“能调用模型”仍然不是 Agent。

**Failure case**

让模型分析一个必须读取本地文件才能回答的问题。单次调用只能猜测或请求更多信息，无法接触环境。

**暂停点**

展示输入、输出和测试后停止，等待学习者确认。

### V0.2：`read_file`——区分工具契约与工具执行

**实现状态：完成，等待学习确认**

验证结果：

- `READ_FILE_TOOL` 以 JSON Schema 描述工具名、用途和 `path` 参数；
- Schema 是不可调用的普通字典，不会自行读取文件；
- `read_file(repository, path)` 能直接读取 Repository 内的 UTF-8 文件；
- 文件不存在、空路径和越界路径会返回稳定的错误 Observation；
- 本小需求没有调用模型，也没有实现自动 Tool Calling。

**本次只做**

- 定义 `read_file` 的最小 Tool Schema；
- 实现一个由 Harness 直接调用的 `read_file`；
- 处理成功、文件不存在和无效参数；
- 此时不让模型自动调用工具。

**学习重点**

- Tool Schema 是给模型看的能力描述；
- Python 函数才是 Harness 中真正执行动作的实现；
- “模型选择工具”和“程序执行工具”是两个不同步骤。

**Failure case**

仅把 schema 交给模型但不执行它，观察模型虽然能生成 tool call，却得不到文件内容。

**暂停点**

直接运行工具测试并解释输入、输出和错误后停止。

### V0.3：单次 Tool Calling 往返——先不用循环

**实现状态：完成，等待学习确认**

验证结果：

- 第一次请求同时发送用户任务和 `READ_FILE_TOOL` Schema；
- 模型返回 `read_file` 的 Tool Call 后，Harness 解析名称和 JSON 参数；
- Harness 通过一个普通 `if` 分发并执行 Python `read_file`；
- 消息历史按 user → assistant tool call → tool result 的顺序构造；
- Tool Result 使用原始 `tool_call_id`，第二次请求能基于文件内容回答；
- 故意使用错误 `tool_call_id` 时，DeepSeek 返回 HTTP 400；
- 为支持确定性的 `required` / `none` 实验，本阶段显式关闭 DeepSeek Thinking Mode；
- 当前流程固定调用两次模型，没有 `while` 循环。

**本次只做**

- 第一次调用 LLM，让模型请求 `read_file`；
- Harness 执行工具并回填结果；
- 第二次调用 LLM，让模型基于文件内容回答；
- 流程先明确写成两个调用，不抽象成 `while`。

**学习重点**

- assistant tool call 和 tool result 在消息历史中的顺序；
- tool call 标识为什么必须正确关联；
- Observation 如何让第二次推理有别于第一次。

**Failure case**

尝试漏掉 assistant tool-call 消息、漏掉结果或使用错误标识，观察消息协议如何失败。

**暂停点**

逐条展示消息历史变化后停止。

### V0.4：最小 `while` Agent Loop

**本次只做**

- 将 V0.3 的两次固定调用推广为循环；
- 支持连续多次 `read_file`；
- 无 tool call 时结束；
- 加入固定的最大迭代次数。

**学习重点**

- Agent Loop 本质上是由 Harness 控制的状态机；
- `messages` 如何成为 V0 的最小状态；
- 模型决定下一动作，Harness 决定是否以及如何执行。

**Failure case**

构造一个始终请求工具的假模型，观察没有最大轮数时为什么无法安全结束。

**暂停点**

展示多轮轨迹、终止条件和测试后停止。

### V0.5：`shell` 与失败观察

**本次只做**

- 加入最小 `shell` 工具；
- 固定在用户指定仓库中执行；
- 返回退出码、标准输出和标准错误；
- 设置固定超时；
- 将非零退出、超时和工具参数错误作为 observation 回填模型。

**学习重点**

- Tool error 为什么通常应成为模型可见的观察，而不是直接终止 Agent；
- 命令执行结果应保留哪些信息；
- 工具失败与 Harness 自身崩溃的区别。

**Failure case**

执行一个失败命令，让模型读取 stderr 后选择新的命令或解释失败。

**暂停点**

分别展示成功、非零退出和超时轨迹后停止。

### V0.6：CLI、端到端实验与 V0 总复盘

**本次只做**

- 提供 `mini-codex <repository> <task>` 入口；
- 串联此前已经确认的能力；
- 完成确定性端到端测试；
- 在受控 Demo Repository 中完成一次真实模型实验；
- 对照 V0 Definition of Done 进行验收。

**学习重点**

- 用户任务怎样进入消息历史；
- 仓库路径怎样影响工具运行环境；
- 一条完整 Agent 轨迹如何从任务走到最终回复；
- 为什么 V0 的“模型停止调用工具”仍不等于“任务已经严格验证完成”。

**暂停点**

完成 V0 总复盘并等待明确确认。未确认前不进入 V1。

## 5. 每个小需求的固定交付格式

每完成 V0.x，Coding Partner 必须提供：

1. **本次结果**：新增了什么可观察能力；
2. **Why / Without It / How 回顾**；
3. **代码导读**：只解释本次新增的数据流；
4. **验证证据**：测试和最小运行示例；
5. **Failure case**：展示缺失机制或错误输入的行为；
6. **边界与 trade-off**：说明刻意没有解决什么；
7. **学习确认问题**：请学习者用自己的语言复述关键点；
8. **停止开发**：等待明确确认后再进入下一小需求。

## 6. V0 Definition of Done

### 功能

- 命令行能够接收 Repository 路径和用户任务；
- LLM 可以请求 `read_file` 和 `shell`；
- Harness 能执行工具并正确回填结果；
- 模型能消费 Observation 后继续选择动作；
- 普通最终回复、工具失败和最大轮数均有明确路径；
- `shell` 在目标 Repository 中执行并有固定超时。

### 测试

- 每个小需求都有不依赖网络的确定性测试；
- 覆盖 `read_file` 成功与失败；
- 覆盖 `shell` 成功、非零退出与超时；
- 假模型能够驱动“读文件 → 运行命令 → 最终回复”的完整轨迹；
- 至少完成一次真实模型 smoke test。

### 学习

学习者能够：

- 画出 Tool Calling 的完整消息流；
- 解释模型、Harness 和工具环境的职责；
- 说明 assistant tool call 与 tool result 的对应关系；
- 解释普通结束、工具失败和最大轮数终止；
- 用一个 failure case 说明为什么单轮调用不是 Agent。

## 7. 明确非目标

V0 不提供专用写文件、编辑、搜索或 Git Diff 工具，不实现 Tool Registry、Context Manager、Planning、持久化 State、Compaction、Checkpoint、Sandbox、Permission、Tracing、Evaluation 或 Subagent。

V0 的 `shell` 仍在宿主环境执行，因此只在受控仓库和安全命令中实验。安全隔离将在 V6 专门学习和实现。
