import json
from pathlib import Path

from mini_codex.tools import READ_FILE_TOOL, SHELL_TOOL, read_file, shell


def run_read_file_round_trip(
    task: str, repository: Path, *, model: str, client
) -> str:
    messages = [{"role": "user", "content": task}]
    first_response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=[READ_FILE_TOOL],
        tool_choice="required",
        extra_body={"thinking": {"type": "disabled"}},
    )

    assistant_message = first_response.choices[0].message
    messages.append(assistant_message)

    tool_call = assistant_message.tool_calls[0]
    if tool_call.function.name != "read_file":
        raise ValueError(f"Unsupported tool: {tool_call.function.name}")

    arguments = json.loads(tool_call.function.arguments)
    tool_result = read_file(repository, arguments["path"])
    messages.append(
        {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": tool_result,
        }
    )

    second_response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=[READ_FILE_TOOL],
        tool_choice="none",
        extra_body={"thinking": {"type": "disabled"}},
    )
    return second_response.choices[0].message.content


def run_agent_loop(
    task: str,
    repository: Path,
    *,
    model: str,
    client,
    max_iterations: int = 5,
) -> str:
    # messages 是 V0 的最小运行状态；每轮都会把完整历史重新发送给模型。
    messages = [{"role": "user", "content": task}]
    iteration = 0

    while iteration < max_iterations:
        # auto 让模型选择“调用工具”或“直接结束”，循环边界仍由 Harness 控制。
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=[READ_FILE_TOOL, SHELL_TOOL],
            tool_choice="auto",
            extra_body={"thinking": {"type": "disabled"}},
        )
        iteration += 1
        assistant_message = response.choices[0].message
        # Tool Result 必须跟在发起 Tool Call 的 assistant message 后面。
        messages.append(assistant_message)

        tool_calls = getattr(assistant_message, "tool_calls", None)
        # 没有 Tool Call 表示模型已经给出最终回答，Agent Loop 正常结束。
        if not tool_calls:
            return assistant_message.content

        for tool_call in tool_calls:
            # 模型只负责提出请求；Harness 负责校验并执行真正的 Python 函数。
            arguments = json.loads(tool_call.function.arguments)
            if tool_call.function.name == "read_file":
                tool_result = read_file(repository, arguments["path"])
            elif tool_call.function.name == "shell":
                tool_result = shell(repository, arguments.get("command"))
            else:
                raise ValueError(f"Unsupported tool: {tool_call.function.name}")

            messages.append(
                {
                    "role": "tool",
                    # 这个 ID 让模型知道 Observation 属于哪一个 Tool Call。
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                }
            )

    # 模型在调用预算内始终没有结束，Harness 强制中止无限循环。
    raise RuntimeError(
        f"Agent reached max_iterations={max_iterations} without finishing"
    )
