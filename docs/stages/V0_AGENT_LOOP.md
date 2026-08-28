# V0：最小 Agent Loop

## 状态

- 总方向：已确认
- V0.0：已确认
- V0.1：已确认
- V0.2：已确认
- V0.3：已确认；可重复运行的 DeepSeek Smoke Test 已补充
- V0.4：已确认
- V0.5：已确认
- V0.6：实现与技术验收完成，等待 V0 总学习复盘确认

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

**实现状态：已确认**

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

**实现状态：已确认**

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

**实现状态：已确认**

验证结果：

- 第一次请求同时发送用户任务和 `READ_FILE_TOOL` Schema；
- 模型返回 `read_file` 的 Tool Call 后，Harness 解析名称和 JSON 参数；
- Harness 通过一个普通 `if` 分发并执行 Python `read_file`；
- 消息历史按 user → assistant tool call → tool result 的顺序构造；
- Tool Result 使用原始 `tool_call_id`，第二次请求能基于文件内容回答；
- 故意使用错误 `tool_call_id` 时，DeepSeek 返回 HTTP 400；
- 为支持确定性的 `required` / `none` 实验，本阶段显式关闭 DeepSeek Thinking Mode；
- 当前流程固定调用两次模型，没有 `while` 循环。

可重复运行的真实 API 实验保存在 `examples/v0_3_deepseek_smoke.py`：

```bash
set -a
source .env
set +a
PYTHONPATH=src .venv/bin/python examples/v0_3_deepseek_smoke.py
```

它复用正式的 `run_read_file_round_trip`，只在外层观察并打印两次请求和响应。
因此这里看到的是 DeepSeek 的真实 Tool Call，而不是脚本伪造的 Tool Call。
自动化测试则注入 Fake Client，以便稳定验证输出结构且不消耗 API 额度。

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

**实现状态：已确认**

#### Why

真实任务需要的工具调用次数无法预先确定。模型可能直接回答，也可能读取一个文件后继续读取另一个文件。Harness 因此不能把流程写死为“两次模型调用”，而要根据每轮响应决定继续还是结束。

#### Without It

V0.3 在第一次请求中强制调用工具，在第二次请求中禁止调用工具。如果第二次推理发现还需要读取其他文件，模型也无法继续请求工具。固定往返只能演示 Tool Calling 协议，不能形成可持续运行的 Agent Loop。

#### How

新增独立的 `run_agent_loop`，同时保留 V0.3 的 `run_read_file_round_trip` 作为对照。循环中的每一轮都显式使用 `tool_choice="auto"`：模型可以请求工具，也可以返回最终文本。

```text
messages = [user task]
iteration = 0

while iteration < max_iterations:
    调用 LLM
    iteration += 1
    追加 assistant message

    if 没有 tool calls:
        返回 assistant content

    for 当前回复中的每个 tool call:
        校验工具名
        解析 arguments
        执行 read_file
        追加对应的 tool result

raise RuntimeError
```

#### 接口与职责

新函数采用以下最小接口：

```python
run_agent_loop(
    task,
    repository,
    *,
    model,
    client,
    max_iterations=5,
) -> str
```

- `task` 生成第一条 user message；
- `repository` 限制 `read_file` 的读取范围；
- `client` 执行模型调用，测试时可以注入 Fake Client；
- `max_iterations` 统计 LLM 调用次数，而不是工具调用次数；
- 返回值是第一条不含 Tool Call 的 assistant message 内容。

本阶段不提取 Tool Registry、工具分发器类或独立 State 对象。`messages` 列表仍是 V0 唯一的最小运行状态。

#### 消息与状态变化

一次“读取两个文件再回答”的轨迹应为：

```text
messages[0]  user task
messages[1]  assistant: read_file(A)
messages[2]  tool: A 的内容
messages[3]  assistant: read_file(B)
messages[4]  tool: B 的内容
messages[5]  assistant: final answer
```

每轮调用都会发送当时完整的 `messages`。模型没有内部记忆；它能理解前序 Tool Result，是因为 Harness 在下一轮重新发送了这些消息。

如果模型在同一条 assistant message 中返回多个 Tool Call，Harness 会依次执行并回填全部结果，然后才开始下一轮模型调用。每个结果必须使用各自原始的 `tool_call_id`。

#### 终止与错误

只有两种循环终止路径：

1. 模型返回不含 Tool Call 的消息：正常结束并返回文本；
2. 已完成 `max_iterations` 次 LLM 调用但模型仍请求工具：抛出 `RuntimeError`。

达到上限时不返回模型文本，因为 Harness 的强制停止不是模型完成任务。未知工具名仍抛出 `ValueError`；文件不存在等 `read_file` 结果仍作为普通 Observation 回填。更完整的工具失败恢复留到 V0.5。

#### 方案权衡

采用“新增循环函数、保留 V0.3 函数”，可以直接比较固定往返与 Agent Loop，代价是暂时存在少量重复代码。直接改写旧函数会失去 V0.3 实验基线；提前抽取公共层虽然减少重复，却会遮住本阶段最需要观察的循环和消息变化。

#### TDD 验收案例

- 模型首轮没有 Tool Call：只调用一次模型并直接返回；
- 模型连续两轮请求 `read_file`：第三轮基于两个结果回答；
- 每一轮请求都显式使用 `tool_choice="auto"`；
- 同一轮多个 Tool Call：所有结果都按正确 ID 回填；
- 模型持续请求工具：达到最大 LLM 调用次数后抛出 `RuntimeError`。

#### 验证结果

- 5 个 V0.4 测试覆盖直接结束、连续读取、同轮多调用、最大轮数和未知工具；
- 仓库全部 17 个测试通过；
- 真实 DeepSeek 使用 `tool_choice="auto"` 完成三次 LLM 调用；
- 第一轮请求 `README.md`，第二轮看到结果后请求 `docs/stages/V0_AGENT_LOOP.md`；
- 第三轮消费两个 Tool Result 后返回最终答案，没有继续请求工具。

真实轨迹：

```text
MODEL CALL 1 → read_file(README.md)
MODEL CALL 2 → observe README → read_file(docs/stages/V0_AGENT_LOOP.md)
MODEL CALL 3 → observe V0 document → final answer
```

**本次只做**

- 将 V0.3 的两次固定调用推广为循环；
- 支持连续多次 `read_file`；
- 无 tool call 时结束；
- 加入默认值为 5 的最大迭代次数参数。

**学习重点**

- Agent Loop 本质上是由 Harness 控制的状态机；
- `messages` 如何成为 V0 的最小状态；
- 模型决定下一动作，Harness 决定是否以及如何执行。

**Failure case**

构造一个始终请求工具的假模型，观察没有最大轮数时为什么无法安全结束。

**暂停点**

展示多轮轨迹、终止条件和测试后停止。

### V0.5：`shell` 与失败观察

**实现状态：已确认**

#### Why

读取文件只能让 Agent 理解代码，不能让它验证代码。测试、构建、静态检查和 Git 状态都需要在真实 Repository 中执行命令，并把执行结果交还模型继续推理。

#### Without It

没有 `shell` 时，模型可以建议“运行测试”，但看不到退出码、stdout 或 stderr。它无法知道测试是否通过，也不能根据失败信息修改下一步。Agent Loop 虽然能够循环，却仍缺少“行动并观察”的关键环境能力。

#### How

在 `tools.py` 中增加 `SHELL_TOOL` Schema 和一个直接可读的 `shell` 函数。工具负责执行命令并把所有可预期结果归一化为 JSON Observation；Agent Loop 只通过普通 `if/elif` 在 `read_file` 与 `shell` 之间分发，不引入 Tool Registry。

#### Tool Schema 与接口

模型只看到一个字符串参数：

```json
{
  "name": "shell",
  "arguments": {
    "command": "python -m unittest"
  }
}
```

Python 实现采用：

```python
shell(
    repository,
    command,
    timeout_seconds=10,
) -> str
```

`timeout_seconds` 是 Harness 内部参数，不暴露在 Tool Schema 中，因此模型不能延长超时。测试可以传入更短的值，避免真的等待 10 秒。

#### 命令执行

最小版本使用标准库：

```python
subprocess.run(
    command,
    cwd=repository,
    shell=True,
    capture_output=True,
    text=True,
    timeout=timeout_seconds,
    check=False,
)
```

- `cwd=repository` 将命令工作目录固定为用户指定的 Repository；
- 字符串命令支持管道、重定向和组合命令；
- `check=False` 让非零退出成为数据，而不是 Python 异常；
- 默认 10 秒超时由 Harness 控制。

#### Observation 格式

所有正常、非零退出、参数错误和超时结果都返回同样四个字段的 JSON 字符串：

```json
{
  "exit_code": 1,
  "stdout": "",
  "stderr": "test failed",
  "timed_out": false
}
```

具体语义：

- 成功：`exit_code` 为 `0`；
- 命令失败：保留真实非零退出码；
- 超时：`exit_code` 为 `null`、`timed_out` 为 `true`，并保留已经捕获的输出；
- `command` 缺失、不是字符串或去除空白后为空：`exit_code` 为 `null`，错误原因写入 `stderr`；
- 使用 `json.dumps(..., ensure_ascii=False)`，确保中文输出保持可读。

可解析的参数错误由工具转换为 Observation。无法解析的 Tool Call JSON 仍是消息协议错误，不在本阶段吞掉。

#### Agent Loop 集成

每次模型调用都同时提供两个 Schema：

```text
[READ_FILE_TOOL, SHELL_TOOL]
```

Harness 使用最小分支：

```text
read_file → read_file(repository, path)
shell     → shell(repository, command)
其他工具  → ValueError
```

Shell 的非零退出和超时结果不会结束 Agent Loop。Harness 使用原始 `tool_call_id` 把 JSON Observation 追加到 `messages`，下一轮模型可以读取 stderr、修正命令或解释失败。

#### 错误分类

- 命令返回非零退出码：工具执行结果，回填模型；
- 命令超时：工具执行结果，回填模型；
- `command` 参数无效：工具参数错误，回填模型；
- 未知工具名或无法解析 Tool Call JSON：Harness/协议错误，抛出异常；
- Repository 路径本身无效：Harness 初始化错误，不伪装成 Shell 命令失败。

这个区分让模型能够从环境失败中恢复，同时不掩盖 Harness 自身的编程错误。

#### 安全边界

V0.5 的 `shell` 使用宿主机环境执行字符串命令，没有 Sandbox、Permission、命令白名单、网络隔离或环境变量隔离。实验只运行受控 Repository 中的安全命令。完整安全执行环境留到 V6。

本阶段也不实现输出截断或 Context Budget；超大命令输出的 Context 风险留到 V2/V4。标准库超时只提供最小等待上限，不承诺完整清理命令产生的所有子进程。

#### 方案权衡

让 `shell` 直接返回 JSON 字符串，会把执行和结果归一化放在同一个函数中，但能让 Agent Loop 保持只负责消息与分发。返回 `CompletedProcess` 再由 Agent 格式化会泄漏 subprocess 细节；引入 `ToolResult`、异常层和 Tool Registry 则超出 V0.5 的学习范围。

#### TDD 验收案例

- `SHELL_TOOL` 正确描述必填字符串参数 `command`；
- 命令在指定 Repository 中运行并捕获 stdout；
- stderr 和非零退出码被写入 JSON，而不是抛出异常；
- 超时返回 `timed_out=true`；
- 空白命令和错误类型返回参数错误 Observation；
- Agent Loop 同时向模型提供 `read_file` 与 `shell`；
- 假模型先收到失败 Shell Observation，再发出新动作并最终回答；
- V0.4 的 `read_file` 多轮行为保持不变。

#### 验证结果

- 6 个 V0.5 测试覆盖 Schema、成功执行、非零退出、参数错误、超时和 Agent 失败恢复；
- 仓库全部 23 个测试通过；
- 真实 DeepSeek 使用三次 LLM 调用完成“失败命令 → 成功命令 → 最终回答”；
- 第一条命令退出码为 7，stderr 为 `expected failure`，Agent Loop 没有崩溃；
- 第二轮模型读取失败 JSON 后执行恢复命令，得到退出码 0 和 stdout `recovered`；
- 第三轮模型消费两个 Observation 后正确报告结果并停止调用工具。

真实轨迹：

```text
MODEL CALL 1 → shell(failing command)
TOOL RESULT  → exit_code=7, stderr="expected failure"
MODEL CALL 2 → shell(recovery command)
TOOL RESULT  → exit_code=0, stdout="recovered"
MODEL CALL 3 → final answer
```

**本次只做**

- 加入最小 `shell` 工具；
- 固定在用户指定仓库中执行；
- 返回退出码、标准输出和标准错误；
- 设置由 Harness 控制、模型不可修改的默认 10 秒超时；
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

**实现状态：实现与技术验收完成，等待 V0 总学习复盘确认**

#### Why

目前的 Agent Loop 只能由 Python 代码直接调用。CLI 提供 V0 的用户边界，把 Repository 路径、用户任务和模型配置组装成一次完整运行，使 V0.1 至 V0.5 的能力可以通过最终约定的命令启动。

#### Without It

如果没有 CLI，每次实验都要手动编写 Python 脚本、创建 Client 并调用 `run_agent_loop`。Agent Loop 虽然存在，却还不能通过下面的稳定入口使用：

```bash
mini-codex <repository> "<task>"
```

#### How

新增一个很薄的 `src/mini_codex/cli.py`，并在 `pyproject.toml` 中注册 Console Script：

```text
用户执行 mini-codex
        ↓
pyproject.toml 找到 mini_codex.cli:main
        ↓
argparse 解析 repository 和 task
        ↓
校验 Repository、任务和 API Key
        ↓
从环境变量读取 DeepSeek 配置
        ↓
OpenAI(...) 创建兼容 DeepSeek API 的 Client
        ↓
run_agent_loop(task, repository, ...)
        ↓
打印模型最终回复
```

CLI 只负责输入、配置和组装；`agent.py` 继续负责消息历史与循环，`tools.py` 继续负责真实环境操作，`llm.py` 保留 V0.1 的单次调用基线。本阶段不增加 `config.py`、Client Factory 或 Provider 抽象。

#### CLI 契约与配置

命令只包含两个位置参数：

```bash
mini-codex <repository> "<task>"
```

- `repository` 会转换为绝对路径，并且必须是一个存在的目录；
- `task` 去除空白后必须非空；
- CLI 不要求 Repository 必须包含 `.git`，因为 V0 工具真正需要的是有效工作目录；
- `max_iterations` 不暴露为命令行参数，继续使用 Agent Loop 的默认值 `5`。

模型配置只从当前进程继承的环境变量读取：

```text
DEEPSEEK_API_KEY     必填
DEEPSEEK_BASE_URL    可选，默认 https://api.deepseek.com
MINI_CODEX_MODEL     可选，默认 deepseek-v4-flash
```

CLI 不主动查找或加载 `.env`，因此不增加 `python-dotenv`。本地实验仍由 Shell 通过 `source .env` 导出变量，Mini Codex 只消费环境配置。

#### 错误处理

缺少位置参数、Repository 无效、任务为空或缺少 `DEEPSEEK_API_KEY` 时，CLI 会在创建 Client 和调用模型之前失败，并输出明确错误。

Agent Loop 中的未知工具、无效 Tool Call JSON、模型 API 异常和最大轮数异常不会被伪装成 Tool Result。它们仍作为 Harness 或协议错误向上抛出。Shell 非零退出、超时和工具参数错误则保持现有语义，作为模型可见的 Observation 回填。

#### 确定性端到端测试

新增 `tests/test_cli.py`，使用临时 Repository 和 Fake Client 驱动完整轨迹：

```text
CLI repository + task
        ↓
Fake Model 请求 read_file
        ↓
Harness 读取临时文件
        ↓
Fake Model 请求 shell
        ↓
Harness 在临时 Repository 执行安全命令
        ↓
Fake Model 返回最终回复
        ↓
CLI 打印最终回复
```

测试只替换网络边界上的 Client。`cli.py`、`run_agent_loop`、`read_file` 和 `shell` 都执行真实代码。测试需要证明：

- 两个位置参数被正确解析；
- 环境变量正确进入 Client 和 Agent Loop；
- `read_file` 返回临时文件的真实内容；
- `shell` 在临时 Repository 中运行并返回 JSON Observation；
- Tool Result 使用原始 `tool_call_id`；
- 后续模型请求包含完整消息历史；
- 最终回复写入标准输出；
- Repository 无效或密钥缺失时不会调用模型。

#### 真实 DeepSeek 实验

安装 Console Script、由 Shell 加载 `.env` 后，直接在 Mini Codex Repository 中执行：

```bash
.venv/bin/pip install -e .
source .venv/bin/activate

set -a
source .env
set +a

mini-codex . \
  "先读取 pyproject.toml，然后运行 PYTHONPATH=src python -m unittest -v，最后根据文件内容和测试结果总结项目状态。"
```

实验使用真实 DeepSeek API 和真实 Repository，验证模型能够连续选择 `read_file`、`shell`，消费 Observation 并最终停止。V0.6 不为了显示轨迹而引入正式 Tracing；完整消息协议由确定性测试检查，真实实验负责证明外部 API 与环境链路可以接通。

#### Failure case

移除 `DEEPSEEK_API_KEY` 后运行 CLI，Harness 应在第一次模型调用前失败。这个对照说明 API 配置错误属于 Harness 初始化错误，不应该被追加成 `role="tool"` 的 Observation。

#### 方案权衡与边界

采用 `cli.py` 加 Console Script 可以准确提供目标命令，又不会把 CLI、配置和 Agent Loop 混在一起。只提供 `python -m mini_codex` 会偏离目标命令；提前加入配置层、多供应商 Client Factory 或更多 CLI 选项，则会隐藏 V0 最需要观察的数据流。

V0.6 仍不实现文件编辑、代码搜索、Git Diff、`.env` 自动加载、正式 Tracing、Sandbox、Permission、API 重试或会话持久化。模型不再请求工具，只表示 Agent Loop 达到当前正常终止条件，不代表任务已经被严格验证完成。

#### TDD 验收案例

- 缺少 `DEEPSEEK_API_KEY`：在创建 Client 前退出；
- Repository 不存在或不是目录：在模型调用前退出；
- 完整轨迹：Fake Model 依次请求 `read_file`、`shell`，然后返回最终文本；
- CLI 输出：只把最终回复写入标准输出；
- 安装入口：Editable Install 后 `mini-codex --help` 可运行；
- 真实实验：DeepSeek 在 Mini Codex Repository 中完成只读分析和测试命令。

#### V0.6a 验证结果

V0.6a 只实现 CLI 的正常运行路径，尚未加入友好输入校验或 Console Script 注册。

第一轮 RED/GREEN：

- RED：端到端测试因 `mini_codex.cli` 不存在而失败；
- GREEN：新增最薄的 `cli.py`，解析 Repository 和 Task、读取环境配置、创建 Client、调用 `run_agent_loop` 并打印最终回复；
- 测试中的 Fake Client 只替换网络调用，`run_agent_loop`、`read_file` 和 `shell("pwd")` 都执行真实代码。

第二轮 RED/GREEN：

- RED：自定义 `DEEPSEEK_BASE_URL` 和 `MINI_CODEX_MODEL` 被忽略，测试观察到 Client 仍使用默认地址；
- GREEN：环境变量存在时使用配置值，不存在时分别回退到 `https://api.deepseek.com` 和 `deepseek-v4-flash`。

端到端测试观察到的完整数据流是：

```text
CLI 参数
  ↓
user task
  ↓
assistant: read_file(project.txt)
  ↓
tool: "Mini Codex CLI"
  ↓
assistant: shell("pwd")
  ↓
tool: exit_code=0 + Repository 绝对路径
  ↓
assistant: final answer
  ↓
CLI stdout
```

验证结果：V0.6a 的 2 个 CLI 测试通过，仓库全部 25 个测试通过。V0.6b 才会处理缺少密钥、无效 Repository 和空任务；V0.6c 才会注册并运行真正的 `mini-codex` 命令。

#### V0.6b 验证结果

V0.6b 将三个 Harness 启动错误统一为 `argparse` CLI 错误：

```text
解析 repository 和 task
        ↓
Repository 是有效目录？ ──否──→ stderr + exit code 2
        ↓ 是
Task 去除空白后非空？ ──否──→ stderr + exit code 2
        ↓ 是
DEEPSEEK_API_KEY 存在？ ──否──→ stderr + exit code 2
        ↓ 是
创建 OpenAI Client
        ↓
进入 Agent Loop
```

三轮 RED/GREEN 分别观察到：

- 缺少密钥：RED 暴露裸 `KeyError('DEEPSEEK_API_KEY')`；GREEN 改为 `DEEPSEEK_API_KEY is required`；
- 无效 Repository：RED 证明 CLI 已经尝试创建 Client；GREEN 在路径解析后使用 `is_dir()` 拦截；
- 空白 Task：RED 证明空任务仍会创建 Client；GREEN 使用 `task.strip()` 判断非空，但继续把原始 Task 文本传入 Agent Loop。

每个测试都验证退出码为 `2`、错误原因写入 stderr，并且 `OpenAI(...)` 从未调用。这些错误不会进入 `messages`，也不会生成 `role="tool"` 的 Observation，因为 Agent Loop 尚未启动。

验证结果：V0.6b 新增 3 个启动校验测试，5 个 CLI 测试全部通过，仓库全部 28 个测试通过。V0.6c 才会注册 Console Script 并运行真实 DeepSeek 实验。

#### V0.6c 验证结果

在 `pyproject.toml` 中注册：

```toml
[project.scripts]
mini-codex = "mini_codex.cli:main"
```

安装后，Shell 中的 `mini-codex` 命令会调用 `mini_codex.cli:main`。这里的 Console Script 只负责把命令名映射到现有 Python 函数，不新增 Agent 行为。

打包入口的 RED/GREEN 过程：

- RED：`.venv/bin/mini-codex --help` 返回退出码 `127`，因为命令不存在；
- 第一次 GREEN 尝试：项目虚拟环境中的 pip 21.2.4 不支持仅基于 `pyproject.toml` 的 Editable Install，命令仍未生成；
- 环境恢复：只升级项目 `.venv` 内的 pip，不修改系统 Python；
- GREEN：`pip install -e .` 成功，`mini-codex --help` 返回退出码 `0`，显示 `repository` 和 `task` 两个位置参数。

Editable Install 生成的 `*.egg-info/` 是可再生打包元数据，已加入 `.gitignore`，不会作为项目源码提交。

真实 DeepSeek Smoke Test 首次启动时，V0.6b 检测到当前 `.env` 使用旧变量名 `OPENAI_API_KEY`，而 CLI 契约要求 `DEEPSEEK_API_KEY`，因此在模型调用前以退出码 `2` 停止。实验没有修改或复制密钥文件，只在单次子进程中临时映射变量名后重试。

真实 CLI 随后完成任务并输出：

```text
项目名：mini-codex
Python 版本要求：>=3.9
测试数量：28
测试结果：全部通过（Ran 28 tests ... OK）
```

进程退出码为 `0`。这次实验直接证明安装后的 CLI、真实 DeepSeek API 和最终回复链路已经接通，最终文本也与 Repository 文件及测试结果一致。由于 V0.6 CLI 没有正式 Tracing，这次输出本身不逐条记录真实 Tool Call；精确的 `read_file → shell → final` 消息流由 Fake Client 端到端测试检查，真实工具调用则已在此前可观察的 DeepSeek Smoke Test 中验证。自动化测试再次运行，仓库全部 28 个测试通过。

#### V0 技术验收

V0 Definition of Done 的功能和测试部分已经满足：

- CLI 接收 Repository 和 Task；
- 真实模型可以请求 `read_file` 与 `shell`；
- Harness 能关联 Tool Call 与 Tool Result，并把 Observation 回填下一轮；
- 普通结束、工具失败、最大轮数和初始化错误都有明确路径；
- Shell 固定在目标 Repository 中运行，并有 10 秒超时；
- Fake Client 覆盖完整 `read_file → shell → final` 轨迹；
- 28 个确定性测试全部通过；
- 真实 DeepSeek CLI Smoke Test 通过。

技术验收完成不等于学习验收完成。进入 V1 前仍需完成 V0 总复盘，并由学习者明确确认已经能够解释核心消息流和职责边界。

**本次只做**

- 提供 `mini-codex <repository> <task>` 入口；
- 串联此前已经确认的能力；
- 完成确定性端到端测试；
- 在 Mini Codex Repository 自身完成一次真实模型实验；
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
