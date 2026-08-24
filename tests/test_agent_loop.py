import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from mini_codex import agent
from mini_codex.tools import READ_FILE_TOOL, SHELL_TOOL
from tests.test_agent import FakeClient, model_response


def read_file_call_message(path, call_id):
    tool_call = SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(
            name="read_file",
            arguments=f'{{"path": "{path}"}}',
        ),
    )
    return SimpleNamespace(
        role="assistant",
        content=None,
        tool_calls=[tool_call],
    )


def shell_call_message(command, call_id):
    tool_call = SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(
            name="shell",
            arguments=json.dumps({"command": command}),
        ),
    )
    return SimpleNamespace(
        role="assistant",
        content=None,
        tool_calls=[tool_call],
    )


class AgentLoopTests(unittest.TestCase):
    def test_returns_when_first_response_has_no_tool_call(self):
        self.assertTrue(
            hasattr(agent, "run_agent_loop"),
            "run_agent_loop does not exist yet",
        )

        final_message = SimpleNamespace(content="No tool is needed.", tool_calls=None)
        client = FakeClient([model_response(final_message)])

        with tempfile.TemporaryDirectory() as directory:
            result = agent.run_agent_loop(
                "Answer directly",
                Path(directory),
                model="test-model",
                client=client,
            )

        self.assertEqual(result, "No tool is needed.")
        self.assertEqual(
            client.chat.completions.requests,
            [
                {
                    "model": "test-model",
                    "messages": [{"role": "user", "content": "Answer directly"}],
                    "tools": [READ_FILE_TOOL, SHELL_TOOL],
                    "tool_choice": "auto",
                    "extra_body": {"thinking": {"type": "disabled"}},
                }
            ],
        )

    def test_continues_after_two_consecutive_read_file_calls(self):
        first_call = read_file_call_message("A.txt", "call_a")
        second_call = read_file_call_message("B.txt", "call_b")
        final_message = SimpleNamespace(content="A and B were read.", tool_calls=None)
        client = FakeClient(
            [
                model_response(first_call),
                model_response(second_call),
                model_response(final_message),
            ]
        )

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "A.txt").write_text("alpha", encoding="utf-8")
            (repository / "B.txt").write_text("beta", encoding="utf-8")

            result = agent.run_agent_loop(
                "Read A.txt and B.txt",
                repository,
                model="test-model",
                client=client,
            )

        self.assertEqual(result, "A and B were read.")
        self.assertEqual(len(client.chat.completions.requests), 3)
        self.assertEqual(
            client.chat.completions.requests[2]["messages"],
            [
                {"role": "user", "content": "Read A.txt and B.txt"},
                first_call,
                {
                    "role": "tool",
                    "tool_call_id": "call_a",
                    "content": "alpha",
                },
                second_call,
                {
                    "role": "tool",
                    "tool_call_id": "call_b",
                    "content": "beta",
                },
            ],
        )
        self.assertEqual(
            [request["tool_choice"] for request in client.chat.completions.requests],
            ["auto", "auto", "auto"],
        )

    def test_sends_results_for_every_tool_call_in_one_response(self):
        call_a = read_file_call_message("A.txt", "call_a").tool_calls[0]
        call_b = read_file_call_message("B.txt", "call_b").tool_calls[0]
        two_calls = SimpleNamespace(
            role="assistant",
            content=None,
            tool_calls=[call_a, call_b],
        )
        final_message = SimpleNamespace(content="Both files were read.", tool_calls=None)
        client = FakeClient(
            [model_response(two_calls), model_response(final_message)]
        )

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "A.txt").write_text("alpha", encoding="utf-8")
            (repository / "B.txt").write_text("beta", encoding="utf-8")

            result = agent.run_agent_loop(
                "Read both files",
                repository,
                model="test-model",
                client=client,
            )

        self.assertEqual(result, "Both files were read.")
        self.assertEqual(
            client.chat.completions.requests[1]["messages"],
            [
                {"role": "user", "content": "Read both files"},
                two_calls,
                {
                    "role": "tool",
                    "tool_call_id": "call_a",
                    "content": "alpha",
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_b",
                    "content": "beta",
                },
            ],
        )

    def test_stops_before_exceeding_maximum_model_calls(self):
        first_call = read_file_call_message("A.txt", "call_a")
        second_call = read_file_call_message("A.txt", "call_a_again")
        would_finish_too_late = SimpleNamespace(
            content="This answer required too many calls.",
            tool_calls=None,
        )
        client = FakeClient(
            [
                model_response(first_call),
                model_response(second_call),
                model_response(would_finish_too_late),
            ]
        )

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "A.txt").write_text("alpha", encoding="utf-8")

            with self.assertRaisesRegex(
                RuntimeError,
                "Agent reached max_iterations=2 without finishing",
            ):
                agent.run_agent_loop(
                    "Keep reading A.txt",
                    repository,
                    model="test-model",
                    client=client,
                    max_iterations=2,
                )

        self.assertEqual(len(client.chat.completions.requests), 2)

    def test_rejects_unsupported_tool_name(self):
        unsupported_call = read_file_call_message("A.txt", "call_delete")
        unsupported_call.tool_calls[0].function.name = "delete_file"
        final_message = SimpleNamespace(content="Should not get here.", tool_calls=None)
        client = FakeClient(
            [model_response(unsupported_call), model_response(final_message)]
        )

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "A.txt").write_text("alpha", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Unsupported tool: delete_file"):
                agent.run_agent_loop(
                    "Delete A.txt",
                    repository,
                    model="test-model",
                    client=client,
                )

    def test_returns_shell_failure_to_model_and_continues(self):
        shell_call = shell_call_message(
            "printf 'problem' >&2; exit 7",
            "call_shell",
        )
        final_message = SimpleNamespace(
            content="The command failed with exit code 7.",
            tool_calls=None,
        )
        client = FakeClient(
            [model_response(shell_call), model_response(final_message)]
        )

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            try:
                result = agent.run_agent_loop(
                    "Run a failing command and explain it",
                    repository,
                    model="test-model",
                    client=client,
                )
            except ValueError as error:
                self.fail(f"shell should be a supported tool: {error}")

        self.assertEqual(result, "The command failed with exit code 7.")
        self.assertEqual(
            client.chat.completions.requests[0]["tools"],
            [READ_FILE_TOOL, SHELL_TOOL],
        )
        self.assertEqual(
            client.chat.completions.requests[1]["messages"],
            [
                {
                    "role": "user",
                    "content": "Run a failing command and explain it",
                },
                shell_call,
                {
                    "role": "tool",
                    "tool_call_id": "call_shell",
                    "content": json.dumps(
                        {
                            "exit_code": 7,
                            "stdout": "",
                            "stderr": "problem",
                            "timed_out": False,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        )


if __name__ == "__main__":
    unittest.main()
