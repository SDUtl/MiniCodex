import json
from pathlib import Path

from mini_codex.tools import READ_FILE_TOOL, read_file


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
    messages = [{"role": "user", "content": task}]
    iteration = 0

    while iteration < max_iterations:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=[READ_FILE_TOOL],
            tool_choice="auto",
            extra_body={"thinking": {"type": "disabled"}},
        )
        iteration += 1
        assistant_message = response.choices[0].message
        messages.append(assistant_message)

        tool_calls = getattr(assistant_message, "tool_calls", None)
        if not tool_calls:
            return assistant_message.content

        for tool_call in tool_calls:
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

    raise RuntimeError(
        f"Agent reached max_iterations={max_iterations} without finishing"
    )
