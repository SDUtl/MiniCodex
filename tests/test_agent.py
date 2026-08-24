import copy
import importlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from mini_codex.tools import READ_FILE_TOOL


class FakeCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def create(self, **request):
        self.requests.append(copy.deepcopy(request))
        return self.responses.pop(0)


class FakeClient:
    def __init__(self, responses):
        self.chat = SimpleNamespace(completions=FakeCompletions(responses))


def model_response(message):
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def read_file_call_message(name="read_file"):
    tool_call = SimpleNamespace(
        id="call_readme",
        type="function",
        function=SimpleNamespace(
            name=name,
            arguments='{"path": "README.md"}',
        ),
    )
    message = SimpleNamespace(
        role="assistant",
        content=None,
        reasoning_content="I should read the requested file.",
        tool_calls=[tool_call],
    )
    return message


class ReadFileRoundTripTests(unittest.TestCase):
    def test_first_request_includes_task_and_read_file_schema(self):
        try:
            agent = importlib.import_module("mini_codex.agent")
        except ModuleNotFoundError:
            self.fail("mini_codex.agent does not exist yet")
        self.assertTrue(
            hasattr(agent, "run_read_file_round_trip"),
            "run_read_file_round_trip does not exist yet",
        )

        first_message = read_file_call_message()
        final_message = SimpleNamespace(content="Mini Codex")
        client = FakeClient(
            [model_response(first_message), model_response(final_message)]
        )

        with tempfile.TemporaryDirectory() as directory:
            agent.run_read_file_round_trip(
                "Read README.md",
                Path(directory),
                model="test-model",
                client=client,
            )

        self.assertEqual(
            client.chat.completions.requests[0],
            {
                "model": "test-model",
                "messages": [{"role": "user", "content": "Read README.md"}],
                "tools": [READ_FILE_TOOL],
                "tool_choice": "required",
                "extra_body": {"thinking": {"type": "disabled"}},
            },
        )

    def test_executes_read_file_and_sends_its_result_to_model(self):
        agent = importlib.import_module("mini_codex.agent")
        first_message = read_file_call_message()
        final_message = SimpleNamespace(content="Mini Codex")
        client = FakeClient(
            [model_response(first_message), model_response(final_message)]
        )

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "README.md").write_text("# Mini Codex", encoding="utf-8")

            agent.run_read_file_round_trip(
                "Read README.md",
                repository,
                model="test-model",
                client=client,
            )

        self.assertEqual(
            len(client.chat.completions.requests),
            2,
            "Harness should make a second model call after executing the tool",
        )
        self.assertEqual(
            client.chat.completions.requests[1],
            {
                "model": "test-model",
                "messages": [
                    {"role": "user", "content": "Read README.md"},
                    first_message,
                    {
                        "role": "tool",
                        "tool_call_id": "call_readme",
                        "content": "# Mini Codex",
                    },
                ],
                "tools": [READ_FILE_TOOL],
                "tool_choice": "none",
                "extra_body": {"thinking": {"type": "disabled"}},
            },
        )

    def test_rejects_unsupported_tool_name(self):
        agent = importlib.import_module("mini_codex.agent")
        first_message = read_file_call_message(name="delete_file")
        final_message = SimpleNamespace(content="unused")
        client = FakeClient(
            [model_response(first_message), model_response(final_message)]
        )

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "README.md").write_text("# Mini Codex", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Unsupported tool: delete_file"):
                agent.run_read_file_round_trip(
                    "Read README.md",
                    repository,
                    model="test-model",
                    client=client,
                )

    def test_returns_final_answer_from_second_model_call(self):
        agent = importlib.import_module("mini_codex.agent")
        first_message = read_file_call_message()
        final_message = SimpleNamespace(content="The heading is Mini Codex.")
        client = FakeClient(
            [model_response(first_message), model_response(final_message)]
        )

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "README.md").write_text("# Mini Codex", encoding="utf-8")

            result = agent.run_read_file_round_trip(
                "Read README.md",
                repository,
                model="test-model",
                client=client,
            )

        self.assertEqual(result, "The heading is Mini Codex.")


if __name__ == "__main__":
    unittest.main()
