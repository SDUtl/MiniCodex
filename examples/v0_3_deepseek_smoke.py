import os
from pathlib import Path
from types import SimpleNamespace

from openai import OpenAI

from mini_codex.agent import run_read_file_round_trip


TASK = "Read README.md and report its first Markdown heading exactly."


class ObservedCompletions:
    def __init__(self, completions, emit):
        self.completions = completions
        self.emit = emit
        self.call_number = 0

    def create(self, **request):
        self.call_number += 1
        self.emit(f"MODEL CALL {self.call_number}")
        self.emit(f"tool_choice: {request['tool_choice']}")

        if self.call_number == 2:
            tool_message = request["messages"][-1]
            self.emit(f"tool result for {tool_message['tool_call_id']}:")
            self.emit(tool_message["content"])

        response = self.completions.create(**request)
        assistant_message = response.choices[0].message
        tool_calls = getattr(assistant_message, "tool_calls", None)

        if tool_calls:
            for tool_call in tool_calls:
                self.emit(f"tool call: {tool_call.function.name}")
                self.emit(f"arguments: {tool_call.function.arguments}")
                self.emit(f"tool_call_id: {tool_call.id}")
        else:
            self.emit("assistant content:")
            self.emit(assistant_message.content)

        return response


class ObservedClient:
    def __init__(self, client, emit):
        self.chat = SimpleNamespace(
            completions=ObservedCompletions(client.chat.completions, emit)
        )


def run_smoke(*, client, repository: Path, model: str, emit=print) -> str:
    observed_client = ObservedClient(client, emit)
    answer = run_read_file_round_trip(
        TASK,
        repository,
        model=model,
        client=observed_client,
    )
    emit("FINAL ANSWER")
    emit(answer)
    return answer


if __name__ == "__main__":
    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Set DEEPSEEK_API_KEY before running this smoke test")

    real_client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    run_smoke(
        client=real_client,
        repository=Path(__file__).resolve().parents[1],
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
    )
