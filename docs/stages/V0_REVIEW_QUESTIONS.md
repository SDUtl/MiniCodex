# V0 学习问题与参考答案

本文汇总 Mini Codex V0.1～V0.6 学习过程中出现的核心问题，包括 Coding Partner 的检查点提问和学习者主动提出的疑问。语义重复的问题已经合并，答案以当前仓库实现为准。

建议使用方式：先遮住参考答案独立回答，再对照代码和答案检查理解。本文是 V0 的学习复盘，不代表后续 V1～V8 的最终设计。

## 概念索引

| 概念 | 主要章节 |
| --- | --- |
| LLM、DeepSeek API、OpenAI SDK | V0.1 |
| 模型能力、工具能力、记忆 | V0.1、V0.4 |
| Tool Schema、Python 工具函数 | V0.2 |
| Tool Calling、`choices`、`function.arguments` | V0.3 |
| assistant Tool Call、Tool Result、`tool_call_id` | V0.3 |
| Agent Loop、`messages`、终止条件 | V0.4 |
| Shell、Observation、错误分类 | V0.5 |
| CLI、Repository、Task、环境变量 | V0.6 |
| Fake Client、真实 Smoke Test、证据边界 | V0.3、V0.6 |
| V0 安全边界与非目标 | V0.5、V0.6 |

---

## V0.1：单次 LLM 调用

### Q1：模型、DeepSeek API 和 OpenAI SDK 分别扮演什么角色？

**参考答案**

- 模型提供语言理解、推理和输出生成能力，可以把它理解成“大脑能力”；
- DeepSeek API 把 DeepSeek 模型通过网络服务暴露出来；
- OpenAI SDK 是客户端接入方式，负责按 OpenAI-compatible 协议构造请求、发送 HTTP 请求，并把响应解析成 Python 对象。

当前项目使用 OpenAI SDK，不代表调用的是 OpenAI 模型。`base_url` 指向 DeepSeek，真正提供模型能力的是 DeepSeek API。

**常见误区**

把 SDK 当成模型本身。SDK 只负责通信，不负责推理。

**对应实现**

- `generate_once` — [llm.py](../../src/mini_codex/llm.py)
- DeepSeek Client 创建 — [cli.py](../../src/mini_codex/cli.py)

### Q2：调用 LLM API 后，为什么还不能称为 Agent？

**参考答案**

单次 LLM 调用只完成：

```text
文本输入 → 模型 → 文本输出
```

它没有接触真实环境，不能读取本地文件、执行命令、观察结果，也不能根据 Observation 再次决策。Agent 至少需要 Harness 把“模型决策、环境行动、结果回填、继续推理”串成闭环。

**常见误区**

认为模型能回答代码问题，就等于模型已经读取了本地代码。没有工具或显式 Context 时，它只能依赖请求内容和训练知识。

**对应实现**

- V0.1 基线 — [llm.py](../../src/mini_codex/llm.py)
- V0 Agent Loop — [agent.py](../../src/mini_codex/agent.py)

### Q3：模型为什么不能直接读取本地文件？

**参考答案**

远端模型服务只收到 API 请求中的数据。用户电脑的路径、文件系统和进程不会自动暴露给模型。要读取本地文件，必须由本地 Harness 提供工具，并在用户机器上执行真正的文件操作。

**常见误区**

把模型理解为运行在当前终端里的程序。模型运行在远端服务中，本地 Harness 才运行在当前环境里。

**对应实现**

- 本地文件执行函数 — [tools.py](../../src/mini_codex/tools.py)

### Q4：模型是否天然拥有跨请求记忆？

**参考答案**

没有。每次 Chat Completions 请求都是新的模型调用。模型能理解之前发生了什么，是因为 Harness 在下一次请求中重新发送了 `messages` 历史。

V0.1 只有一条 user message，所以没有多轮状态。V0.4 的 `messages` 列表才成为最小的会话状态。

**常见误区**

认为同一个 Client 或同一个模型名会自动保存上一次对话。Client 只是网络客户端，不是记忆存储。

**对应实现**

- 单次请求 — [llm.py](../../src/mini_codex/llm.py)
- 消息历史 — `run_agent_loop` in [agent.py](../../src/mini_codex/agent.py)

### Q5：真实 API 测试和 Fake Client 测试分别证明什么？

**参考答案**

- 真实 API Smoke Test 证明密钥、网络、SDK、DeepSeek 兼容协议和真实模型能够接通；
- Fake Client 测试用预设响应替代模型网络边界，稳定验证 Harness 如何构造请求、维护消息和执行工具。

两者互补：Fake Client 不证明真实模型会做出正确决策；真实调用也不适合承担全部确定性回归测试。

**常见误区**

认为用了 Fake Client，所有代码都是假的。实际测试通常只替换模型网络边界，其余 Harness 和工具仍可真实执行。

**对应实现**

- Fake Client — [test_agent.py](../../tests/test_agent.py)
- 真实 Smoke Test — [v0_3_deepseek_smoke.py](../../examples/v0_3_deepseek_smoke.py)

---

## V0.2：Tool Schema 与工具执行

### Q1：Tool Schema 是什么？

**参考答案**

Tool Schema 是给模型看的结构化能力说明，描述工具名称、用途、参数类型、必填字段和额外参数规则。它让模型知道“可以请求什么”，但 Schema 本身不会执行任何操作。

**常见误区**

看到 JSON Schema 就认为工具已经注册并会自动运行。Schema 只是协议描述。

**对应实现**

- `READ_FILE_TOOL` — [tools.py](../../src/mini_codex/tools.py)

### Q2：`READ_FILE_TOOL` 和 `read_file` 有什么区别？

**参考答案**

- `READ_FILE_TOOL` 是普通 Python 字典，发给模型作为能力契约；
- `read_file(repository, path)` 是本地 Python 函数，真正访问文件系统并返回内容或错误文本。

可以概括为：

```text
Schema 告诉模型“能做什么”
函数负责“真正去做”
```

**常见误区**

认为模型调用了 Schema 中的函数。模型只能生成结构化请求，不能直接调用本地 Python 对象。

**对应实现**

- Schema 与执行函数 — [tools.py](../../src/mini_codex/tools.py)

### Q3：Harness 是怎样真正触发 `read_file` 的？

**参考答案**

模型返回 Tool Call 后，Harness 读取 `tool_call.function.name` 和参数。当名称等于 `read_file` 时，普通 Python 分支会调用：

```python
tool_result = read_file(repository, arguments["path"])
```

所以“触发”不是神秘机制，而是 Harness 中可以直接看到的 `if` 判断和函数调用。

**常见误区**

认为模型响应到达后，SDK 会自动执行本地函数。当前实现中 SDK 只返回响应对象，分发完全由 Harness 编写。

**对应实现**

- `run_read_file_round_trip`、`run_agent_loop` — [agent.py](../../src/mini_codex/agent.py)

### Q4：模型和工具彼此分离，为什么还能连接起来？

**参考答案**

Harness 是中间桥梁：

```text
模型生成 Tool Call
→ Harness 解析请求
→ Harness 调用本地工具
→ Harness 构造 Tool Result
→ 下一次请求把结果发给模型
```

模型负责决策，工具负责环境行动，Harness 负责协议、调度和状态连接。

**常见误区**

把 Tool Calling 理解为模型远程调用本机函数。模型只是提出请求，真正调用发生在 Harness 进程内。

**对应实现**

- 工具连接过程 — [agent.py](../../src/mini_codex/agent.py)

### Q5：`read_file` 如何限制读取范围？

**参考答案**

函数先把 Repository 和目标路径解析成绝对路径，再用 `target.relative_to(repository)` 检查目标仍位于 Repository 内。`../secret.txt` 之类越界路径会返回错误 Observation。

**常见误区**

认为相对路径天然安全。路径中可以包含 `..`，必须在解析后检查实际目标位置。

**对应实现**

- `read_file` — [tools.py](../../src/mini_codex/tools.py)
- 边界测试 — [test_tools.py](../../tests/test_tools.py)

---

## V0.3：单次 Tool Calling 往返

### Q1：`run_read_file_round_trip` 的完整执行过程是什么？

**参考答案**

流程固定为两次模型调用：

```text
构造 user message
→ 第一次调用模型并要求 Tool Call
→ 保存 assistant Tool Call
→ 解析名称和 arguments
→ 执行 read_file
→ 追加 role="tool" 结果
→ 第二次调用模型并禁止继续调用工具
→ 返回最终文本
```

它演示完整 Tool Calling 协议，但还不是可持续循环。

**常见误区**

认为第二次模型调用会自动记得第一次调用。它能看到历史，是因为 Harness 重新发送了完整 `messages`。

**对应实现**

- `run_read_file_round_trip` — [agent.py](../../src/mini_codex/agent.py)

### Q2：`response.choices` 是什么？

**参考答案**

Chat Completions 兼容协议把候选输出放在 `choices` 列表中。每个 choice 通常包含一个模型生成的 message、结束原因等数据。OpenAI SDK 把服务端 JSON 映射为可用属性访问的 Python 对象。

**常见误区**

认为 `choices` 是 Mini Codex 自己定义的字段。它来自模型 API 的响应协议。

**对应实现**

- 响应读取 — [llm.py](../../src/mini_codex/llm.py)、[agent.py](../../src/mini_codex/agent.py)

### Q3：为什么读取 `choices[0]`？是谁规定的？

**参考答案**

API 协议允许返回一个或多个候选结果，所以使用列表。当前请求没有要求多个候选，服务通常返回一个 choice，因此读取第一个元素。这个结构由 OpenAI-compatible Chat Completions 协议定义，并由 DeepSeek 接口兼容实现。

**常见误区**

认为索引 `0` 表示第一轮对话。它表示响应中的第一个候选，不是消息轮次。

**对应实现**

- `response.choices[0].message` — [agent.py](../../src/mini_codex/agent.py)

### Q4：为什么能预期 `tool_call.function.arguments` 这个结构？

**参考答案**

因为 Function Tool Call 的响应结构由兼容协议约定：每个 Tool Call 包含标识、类型和 function；function 中包含工具名与参数字符串。模型和 API 服务需要按这个结构返回，SDK 再映射为对象属性。

但 Harness 不能假设参数内容永远合法。`arguments` 通常是 JSON 字符串，仍可能出现无效 JSON、缺失字段或类型错误。

**常见误区**

认为 Tool Schema 本身创建了这个 Python 对象结构。Schema 约束模型参数，响应外壳来自 API 协议。

**对应实现**

- Tool Call 解析 — [agent.py](../../src/mini_codex/agent.py)

### Q5：为什么要执行 `json.loads(tool_call.function.arguments)`？

**参考答案**

协议中的 `arguments` 是 JSON 字符串，例如：

```json
{"path":"README.md"}
```

Harness 必须反序列化成 Python 字典，才能通过 `arguments["path"]` 取得参数并调用函数。

**常见误区**

认为 `arguments` 已经是字典。它在当前 SDK 对象中仍是字符串。

**对应实现**

- `json.loads(...)` — [agent.py](../../src/mini_codex/agent.py)

### Q6：为什么执行工具前后都要保留 assistant message？

**参考答案**

assistant message 记录了“模型发起了哪一次 Tool Call”。Tool Result 必须跟在这条请求后，并通过相同 ID 关联。下一轮模型收到二者后，才能理解 Observation 从何而来。

```text
assistant: call_1 = read_file(...)
tool: result for call_1
```

**常见误区**

只发送文件内容，省略 assistant Tool Call。这样会丢失协议上下文，服务端也可能拒绝不匹配的 Tool Result。

**对应实现**

- assistant 与 tool 消息追加 — [agent.py](../../src/mini_codex/agent.py)

### Q7：`tool_call_id` 的作用是什么？

**参考答案**

它把 Tool Result 关联到某一次具体调用，而不只是某个工具名。例如同一轮两次调用 `read_file`，名称相同，但 ID 不同：

```text
call_a → read_file("A.py")
call_b → read_file("B.py")
```

结果必须分别携带 `call_a` 和 `call_b`，模型才能准确对应。

**常见误区**

认为工具名已经足够。一次响应可以多次调用同名工具。

**对应实现**

- Tool Result 构造 — [agent.py](../../src/mini_codex/agent.py)
- 多调用测试 — [test_agent_loop.py](../../tests/test_agent_loop.py)

### Q8：遗漏或使用错误 `tool_call_id` 会怎样？

**参考答案**

消息序列不再满足 Tool Calling 协议。真实 DeepSeek 实验中，错误 ID 会导致 HTTP 400。即使某些服务没有立即拒绝，模型也无法可靠知道结果对应哪次调用。

**常见误区**

认为 ID 只是便于日志查看。它是消息协议的一部分。

**对应实现**

- V0.3 协议说明 — [V0_AGENT_LOOP.md](V0_AGENT_LOOP.md)

### Q9：`tool_choice="required"` 和 `tool_choice="none"` 分别做什么？

**参考答案**

- `required` 要求第一次响应产生 Tool Call，便于稳定演示协议；
- `none` 禁止第二次响应继续调用工具，强制返回文本。

这是 V0.3 的教学实验控制，不是通用 Agent 策略。

**常见误区**

认为模型第二轮“自主决定”不再调用工具。V0.3 是 Harness 明确禁止了工具调用。

**对应实现**

- 固定往返控制 — [agent.py](../../src/mini_codex/agent.py)

### Q10：为什么 V0.3 仍然没有真正的 Agent Loop？

**参考答案**

流程被写死为两次模型调用。第二轮即使发现还需要另一个文件，也不能继续请求工具。只有根据每轮 `tool_calls` 动态决定继续或结束的 `while`，才能处理未知轮数的任务。

**常见误区**

认为“调用过一次工具”就等于 Agent。关键是能否观察结果并按需要持续行动。

**对应实现**

- 固定往返与循环对照 — [agent.py](../../src/mini_codex/agent.py)

---

## V0.4：最小 Agent Loop

### Q1：Agent Loop 的本质是什么？

**参考答案**

Agent Loop 是由 Harness 控制的循环状态机：调用模型、读取模型动作、执行工具、追加 Observation、再次调用模型，直到正常结束或达到强制边界。

```text
LLM → Tool Call → Execute → Observation → LLM → ...
```

**常见误区**

把 Agent Loop 当成模型内部能力。循环实际写在本地 Harness 的 `while` 中。

**对应实现**

- `run_agent_loop` — [agent.py](../../src/mini_codex/agent.py)

### Q2：V0 中 `messages` 为什么可以称为最小状态？

**参考答案**

它记录任务、模型的 Tool Call、工具结果和后续回复。每轮请求都重新发送这份历史，所以模型能够基于之前的行动继续推理。V0 还没有独立的 Plan、Todo 或持久化 State。

**常见误区**

认为 `messages` 是模型内部记忆。它是 Harness 进程中的 Python 列表。

**对应实现**

- `messages` 初始化与追加 — [agent.py](../../src/mini_codex/agent.py)

### Q3：为什么每一轮都要发送完整消息历史？

**参考答案**

模型调用之间没有自动共享的内部会话状态。只有重新发送 user task、assistant Tool Call 和 Tool Result，当前调用才知道任务目标、已经做过什么以及 Observation 从何而来。

**常见误区**

认为只发送最新 Tool Result 就够了。没有原始任务和 Tool Call，上下文关系会丢失。

**对应实现**

- 每轮 `messages=messages` — [agent.py](../../src/mini_codex/agent.py)

### Q4：Agent Loop 有哪两种结束路径？

**参考答案**

1. 模型返回不含 Tool Call 的 assistant message：正常结束并返回文本；
2. 已达到 `max_iterations`，模型仍请求工具：Harness 抛出 `RuntimeError` 强制停止。

第二种是安全中止，不代表任务完成。

**常见误区**

把强制达到上限也当成成功答案。当前实现明确抛错，避免伪装完成。

**对应实现**

- 终止分支 — [agent.py](../../src/mini_codex/agent.py)
- 最大轮数测试 — [test_agent_loop.py](../../tests/test_agent_loop.py)

### Q5：为什么模型不再调用工具，并不代表任务一定正确完成？

**参考答案**

当前 Harness 只观察响应中是否还有 Tool Call，没有独立验证需求、测试、Diff 或最终状态。模型可能误解任务、遗漏步骤、误读 Observation 或过早停止。严格 Verification 是后续阶段的问题。

**常见误区**

把“模型给出最终文本”与“环境中的任务客观完成”画等号。

**对应实现**

- 正常结束条件 — [agent.py](../../src/mini_codex/agent.py)

### Q6：为什么需要 `max_iterations`，不能完全让模型决定？

**参考答案**

模型可能反复调用同一个工具、在失败动作之间循环或始终不返回最终文本。Harness 必须限制 LLM 调用次数，控制无限循环、Token、成本和运行时间。

当前 `max_iterations` 统计模型调用次数，不是工具调用次数。

**常见误区**

认为只要提示模型“适时停止”就足够。安全边界必须由确定性程序控制。

**对应实现**

- `max_iterations` — [agent.py](../../src/mini_codex/agent.py)

### Q7：同一条 assistant message 中有多个 Tool Call 时怎么办？

**参考答案**

Harness 依次执行该消息中的全部 Tool Call，为每个调用追加携带对应 ID 的 Tool Result，然后才进入下一轮模型调用。

**常见误区**

执行第一个工具后立刻重新调用模型，遗漏同一消息中的其他请求。

**对应实现**

- `for tool_call in tool_calls` — [agent.py](../../src/mini_codex/agent.py)
- 多调用测试 — [test_agent_loop.py](../../tests/test_agent_loop.py)

### Q8：模型和 Harness 谁决定下一步，谁决定能否执行？

**参考答案**

模型提出下一动作；Harness 校验工具名和参数、决定是否执行本地函数，并控制循环上限。模型没有直接环境权限，Harness 也不会替模型推理要读哪个文件。

**常见误区**

把“模型选择工具”理解成模型拥有执行权限。决策和执行必须分离。

**对应实现**

- 工具分发与循环边界 — [agent.py](../../src/mini_codex/agent.py)

---

## V0.5：Shell 与失败 Observation

### Q1：为什么 Coding Agent 需要 Shell？

**参考答案**

读取文件只能帮助理解代码，无法验证测试、构建、静态检查或 Git 状态。Shell 让 Agent 能在真实 Repository 中执行命令，观察结果后继续决策。

**常见误区**

认为模型说“测试应该通过”就完成了验证。没有真实命令结果只是推测。

**对应实现**

- `SHELL_TOOL`、`shell` — [tools.py](../../src/mini_codex/tools.py)

### Q2：`subprocess.run(..., check=False)` 的作用是什么？

**参考答案**

`check=False` 让非零退出码作为普通 `CompletedProcess` 返回，Harness 可以读取 `returncode`、stdout 和 stderr，并把失败转换成模型可见的 Observation。

如果使用 `check=True`，非零退出会抛出 `CalledProcessError`，当前最小实现需要额外捕获才能继续。

**常见误区**

认为 `check=False` 表示忽略失败。失败没有被忽略，而是从异常形式转换成数据形式。

**对应实现**

- `shell` — [tools.py](../../src/mini_codex/tools.py)

### Q3：Tool Observation 是什么？

**参考答案**

Tool Observation 是 Agent 执行工具后从环境得到、并回填模型的结果。文件内容、文件不存在、Shell stdout/stderr、非零退出码和超时都可以成为 Observation。

在消息协议中，它通常由 `role="tool"` 的消息承载，并通过 `tool_call_id` 关联原始动作。

**常见误区**

把 Observation 当成一个独立工具。它是环境行动的结果，不是工具名称。

**对应实现**

- Tool Result 消息 — [agent.py](../../src/mini_codex/agent.py)
- Shell JSON 结果 — [tools.py](../../src/mini_codex/tools.py)

### Q4：Shell Observation 为什么要保留 `exit_code`、stdout、stderr 和 `timed_out`？

**参考答案**

- `exit_code` 表示命令是否按进程语义成功；
- stdout 保存正常输出；
- stderr 保存诊断信息；
- `timed_out` 区分超时与普通非零退出。

固定结构让模型和测试不必根据异常类型猜测结果格式。

**常见误区**

只保留 stdout。大量测试和编译错误主要写入 stderr，退出码也比文本更可靠。

**对应实现**

- Shell 结果归一化 — [tools.py](../../src/mini_codex/tools.py)

### Q5：Tool 失败、Harness/协议错误、初始化错误有什么区别？

**参考答案**

| 类型 | 例子 | 当前处理 |
| --- | --- | --- |
| Tool 失败 | 测试退出码 1、文件不存在、命令超时 | 作为 Observation 回填，循环可继续 |
| Harness/协议错误 | 未知工具名、Tool Call JSON 无法解析 | 抛出异常，中断运行 |
| 初始化错误 | API Key 缺失、Repository 无效、Task 为空 | CLI 在模型调用前退出 |

区分标准是：这个结果是否来自一次可识别的工具行动，以及模型是否有机会根据它恢复。

**常见误区**

把所有失败都捕获后发给模型，这会掩盖 Harness 自身 Bug；或把所有非零退出都当成程序崩溃，模型就无法恢复。

**对应实现**

- 工具分发 — [agent.py](../../src/mini_codex/agent.py)
- CLI 初始化校验 — [cli.py](../../src/mini_codex/cli.py)

### Q6：stderr 是怎样进入下一轮模型 Context 的？

**参考答案**

`shell` 把 stderr 序列化进 JSON 字符串；Harness 再把该字符串放入 `role="tool"` 消息并追加到 `messages`。下一次 LLM 请求重新发送完整 `messages`，模型因此能读取错误并调整动作。

**常见误区**

认为 subprocess 的 stderr 会自动传到模型。只有 Harness 明确保存并回填，它才会进入 Context。

**对应实现**

- `shell` 与 `messages.append` — [tools.py](../../src/mini_codex/tools.py)、[agent.py](../../src/mini_codex/agent.py)

### Q7：超时为什么由 Harness 控制，而不暴露给模型？

**参考答案**

超时是执行安全和资源控制边界。如果模型能任意延长超时，就可能让 Agent 长时间阻塞。V0 把默认值固定为 10 秒，测试可以直接调用 Python 函数传入更短时间。

**常见误区**

认为超时等于完整进程隔离。标准库超时只是最小等待上限，不承诺清理命令产生的所有子进程。

**对应实现**

- `timeout_seconds` — [tools.py](../../src/mini_codex/tools.py)

### Q8：V0 的 Shell 安全吗？

**参考答案**

不安全。当前 Shell 使用宿主机环境、`shell=True`，没有 Sandbox、Permission、命令白名单、网络隔离或环境变量隔离。`cwd=repository` 只设置初始工作目录，不阻止绝对路径、`cd ..`、写入或删除。

V0 实验只运行受控安全命令；系统级隔离留到 V6。

**常见误区**

认为设置 `cwd` 就限制了命令只能访问 Repository。

**对应实现**

- `shell` — [tools.py](../../src/mini_codex/tools.py)
- V0 安全边界 — [V0_AGENT_LOOP.md](V0_AGENT_LOOP.md)

---

## V0.6：CLI 与端到端链路

### Q1：CLI 在 Harness 中负责什么？

**参考答案**

CLI 负责接收 Repository 和 Task、校验启动输入、读取环境配置、创建 Client、调用 `run_agent_loop` 并打印最终回复。它不负责分析 Tool Call 或直接执行工具。

**常见误区**

把 CLI 写成第二个 Agent Loop，导致消息、工具分发和终止逻辑重复。

**对应实现**

- `main` — [cli.py](../../src/mini_codex/cli.py)

### Q2：为什么 CLI 不直接调用 `read_file` 和 `shell`？

**参考答案**

具体调用哪个工具、调用几次取决于模型每轮决策，这属于 Agent Loop。CLI 只负责启动。如果 CLI 也解析 Tool Call、执行工具和追加结果，它就在重复实现 Agent Loop。

**常见误区**

因为“不知道模型何时输出正确答案”，就让 CLI 接管工具。正确做法是让 Agent Loop 控制协议，让后续 Verification 判断完成质量。

**对应实现**

- CLI 与 Agent 边界 — [cli.py](../../src/mini_codex/cli.py)、[agent.py](../../src/mini_codex/agent.py)

### Q3：CLI 怎样接收 Repository 和 Task？

**参考答案**

Console Script 启动 `main()` 时，`argparse.parse_args(None)` 默认读取 Shell 的命令行参数：

```bash
mini-codex ./demo-repo "读取 README.md"
```

会得到：

```text
arguments.repository = "./demo-repo"
arguments.task = "读取 README.md"
```

Repository 被解析为绝对路径，Task 被传给 `run_agent_loop`。

**常见误区**

认为 CLI 会从自然语言中推断 Repository。Repository 是独立的位置参数。

**对应实现**

- 参数解析 — [cli.py](../../src/mini_codex/cli.py)

### Q4：Task 怎样进入第一次模型请求？

**参考答案**

数据流是：

```text
CLI task
→ arguments.task
→ run_agent_loop(task, ...)
→ {"role": "user", "content": task}
→ 第一次 chat.completions.create
```

CLI 不拆解或改写 Task。`strip()` 只用于检查它是否全为空白。

**常见误区**

认为 CLI 会先让模型总结 Task。V0 没有 Task Initialization 层。

**对应实现**

- Task 传递 — [cli.py](../../src/mini_codex/cli.py)、[agent.py](../../src/mini_codex/agent.py)

### Q5：Repository 参数对工具有什么影响？

**参考答案**

- `read_file` 把相对文件路径解析到 Repository 下；
- `shell` 以 Repository 作为初始 `cwd`；
- CLI 只检查它是存在的目录，不要求包含 `.git`。

Repository 是工具运行位置，不会把整个目录自动放入模型 Context。

**常见误区**

认为传入 Repository 后，模型立即知道所有文件内容。

**对应实现**

- Repository 解析 — [cli.py](../../src/mini_codex/cli.py)
- 工具路径使用 — [tools.py](../../src/mini_codex/tools.py)

### Q6：当前是否只实现了读取某个仓库？

**参考答案**

V0 显式提供 `read_file` 和 `shell`，没有专用 `write_file` 或 `edit_file`，因此还不是正式代码修改 Agent。

但当前 Shell 没有隔离，技术上可以通过重定向、脚本或删除命令修改文件。所以准确说法是：V0 能读取指定 Repository 并在其中执行 Shell；学习实验采用只读命令，但代码没有强制只读。

**常见误区**

认为没有 `write_file` 就绝对无法写文件。Shell 本身是广泛能力入口。

**对应实现**

- V0 工具列表 — [agent.py](../../src/mini_codex/agent.py)
- Shell 安全边界 — [tools.py](../../src/mini_codex/tools.py)

### Q7：Shell 手动加载环境变量和 `python-dotenv` 有什么区别？

**参考答案**

手动方案由 Shell 执行 `source .env` 并把变量导出给子进程；Mini Codex 只使用 `os.getenv`。`python-dotenv` 则由 Python 程序主动查找和解析 `.env`。

V0 选择手动加载，减少依赖，并明确“Shell 准备配置、Harness 消费配置”的边界。代价是每个新终端需要重新加载。

**常见误区**

认为 `python-dotenv` 能加密密钥。它只负责加载文本配置，`.env` 仍必须被 Git 忽略。

**对应实现**

- 环境变量读取 — [cli.py](../../src/mini_codex/cli.py)
- 本地配置示例 — [.env.example](../../.env.example)

### Q8：CLI 为什么要在创建 Client 前校验输入？

**参考答案**

无效 Repository、空 Task 和缺少 API Key 都是启动条件不成立。提前失败可以给出明确错误，避免无意义网络请求、Token 消耗和稍后出现的间接异常。

这些错误发生在 Agent Loop 之前，没有 assistant Tool Call 和 `tool_call_id`，所以不能构造 Tool Observation。

**常见误区**

把缺少 API Key 也发给模型恢复。没有密钥时，Harness 根本无法调用模型。

**对应实现**

- CLI 校验 — [cli.py](../../src/mini_codex/cli.py)
- 校验测试 — [test_cli.py](../../tests/test_cli.py)

### Q9：`parser.error(...)` 会发生什么？

**参考答案**

`argparse` 会把 usage 和错误原因写入 stderr，然后抛出 `SystemExit`，退出码为 `2`，表示命令行使用错误。Client 尚未创建，Agent Loop 尚未启动。

**常见误区**

把它当成 Tool 失败。它属于 CLI/Harness 初始化错误。

**对应实现**

- 错误分支 — [cli.py](../../src/mini_codex/cli.py)

### Q10：Fake Client 在 CLI 端到端测试中替换了什么？

**参考答案**

它替换 `OpenAI(...)` 创建的真实 SDK Client，因此不执行真实 HTTP 请求、DeepSeek 推理或 Token 消耗。它按顺序返回预设 assistant messages。

真实执行的仍包括 CLI 参数解析、环境读取、Agent Loop、消息追加、JSON 参数解析、`read_file`、`shell("pwd")` 和 stdout 输出。

**常见误区**

认为 Fake Client 测试可以证明 DeepSeek 一定选择正确工具。它证明的是：如果模型给出这些动作，Harness 能正确执行协议。

**对应实现**

- CLI 端到端测试 — [test_cli.py](../../tests/test_cli.py)

### Q11：Console Script 怎样把 `mini-codex` 连接到 Python 函数？

**参考答案**

`pyproject.toml` 注册：

```toml
[project.scripts]
mini-codex = "mini_codex.cli:main"
```

安装项目时，打包工具在虚拟环境中生成可执行入口。执行 `mini-codex` 会导入 `mini_codex.cli` 并调用 `main()`。

**常见误区**

认为 Shell 命令名来自 `cli.py` 文件名。它由项目元数据显式注册。

**对应实现**

- Console Script — [pyproject.toml](../../pyproject.toml)

### Q12：真实 CLI Smoke Test 和确定性端到端测试的证据边界是什么？

**参考答案**

- 真实 CLI 实验证明安装入口、环境配置、真实 DeepSeek API 和最终回复链路可以接通；
- Fake Client 端到端测试精确检查 `read_file → shell → final` 的每条 message 和 Tool Result；
- 因为 V0.6 CLI 没有正式 Tracing，单看真实最终文本不能逐条审计真实 Tool Call 轨迹。

所以不能把“最终回答看起来正确”写成完整轨迹的直接证据。

**常见误区**

把结果证据、轨迹证据和确定性协议测试混为一谈。

**对应实现**

- 真实实验与证据说明 — [V0_AGENT_LOOP.md](V0_AGENT_LOOP.md)
- 确定性轨迹 — [test_cli.py](../../tests/test_cli.py)

---

## V0 综合复盘

### Q1：请画出 V0 的完整运行链路。

**参考答案**

```text
mini-codex <repository> <task>
        ↓
CLI 校验并创建 Client
        ↓
messages = [user task]
        ↓
Agent Loop 调用模型
        ↓
模型生成 Tool Call
        ↓
Harness 校验、解析并分发
        ↓
工具操作真实环境
        ↓
Harness 追加 role="tool" Observation
        ↓
完整 messages 再次调用模型
        ↓
继续 Tool Call / 返回最终文本 / 达到上限
```

**常见误区**

漏掉 assistant Tool Call，直接从模型跳到 Tool Result；或认为工具结果会自动回到模型。

**对应实现**

- CLI — [cli.py](../../src/mini_codex/cli.py)
- Agent Loop — [agent.py](../../src/mini_codex/agent.py)
- 工具 — [tools.py](../../src/mini_codex/tools.py)

### Q2：模型、Harness 和工具环境分别负责什么？

**参考答案**

- 模型：根据 Context 生成下一动作或最终文本；
- Harness：维护消息与循环，校验、分发、回填并控制边界；
- 工具环境：真正读取文件、创建进程并产生原始环境结果。

**常见误区**

让模型直接拥有环境权限，或让 Harness 替模型决定业务动作。

**对应实现**

- 三层边界 — [agent.py](../../src/mini_codex/agent.py)、[tools.py](../../src/mini_codex/tools.py)

### Q3：普通结束、Tool 失败和强制停止有什么区别？

**参考答案**

- 普通结束：模型没有 Tool Call，Harness 返回文本；
- Tool 失败：环境行动得到失败结果，作为 Observation 回填，循环通常继续；
- 强制停止：达到 `max_iterations`，Harness 抛出 `RuntimeError`，任务没有被标记成功。

Harness/协议错误与初始化错误是另外两类，会在各自边界中止。

**常见误区**

认为任意 Tool 非零退出都会自动结束 Agent Loop。

**对应实现**

- 终止与错误路径 — [agent.py](../../src/mini_codex/agent.py)、[cli.py](../../src/mini_codex/cli.py)

### Q4：用一个 Failure Case 说明为什么单轮调用不是 Agent。

**参考答案**

要求模型回答本地 `README.md` 的标题。单轮调用拿不到文件，只能猜测或请求用户提供内容。加入 Tool Calling 和 Agent Loop 后，模型可以请求 `read_file`，Harness 读取真实文件，模型再基于 Observation 回答。

差异不在于“回答了几段文本”，而在于是否形成环境反馈闭环。

**常见误区**

把模型根据常识猜对的答案当成读取本地环境的证据。

**对应实现**

- V0.1 基线 — [llm.py](../../src/mini_codex/llm.py)
- V0.3/V0.4 — [agent.py](../../src/mini_codex/agent.py)

### Q5：V0 已经完成什么，为什么还需要 V1？

**参考答案**

V0 已经完成最小 Agent Loop：真实模型调用、Tool Calling、消息历史、`read_file`、`shell`、Observation 回填、循环、终止边界和 CLI。

V0 没有专用编辑、搜索、Glob、Git Diff 或 Tool Registry，也没有严格 Verification。Shell 虽然能力很广，但不透明且不安全。V1 将把“能循环的 Agent”推进为更清晰、可控的 Coding Agent Tool Runtime。

**常见误区**

因为 Shell 理论上能完成许多操作，就跳过专用工具设计。专用工具的 Schema、输入校验、Observation 和权限边界正是 V1 的学习目标。

**对应实现**

- V0 Definition of Done — [V0_AGENT_LOOP.md](V0_AGENT_LOOP.md)
- 项目路线 — [PROJECT_CHARTER.md](../PROJECT_CHARTER.md)

---

## V0 最终自测标准

在进入 V1 前，应能够不看答案解释：

1. 为什么模型不能直接访问本地 Repository；
2. Tool Schema、Tool Call、Python 工具函数和 Tool Result 的区别；
3. `choices[0].message`、`function.arguments` 和 `tool_call_id` 的协议含义；
4. `messages` 如何成为 V0 的最小状态；
5. Agent Loop 为什么需要 Harness 控制的终止边界；
6. Tool Observation 与 Harness 错误为什么必须区分；
7. CLI 如何把 Repository 和 Task 送入 Agent Loop；
8. Fake Client 测试和真实 Smoke Test 各自能证明什么；
9. 当前 Shell 为什么既有用又危险；
10. 为什么模型停止调用工具不等于任务已经验证完成。
