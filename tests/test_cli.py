import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tests.test_agent import FakeClient, model_response
from tests.test_agent_loop import read_file_call_message, shell_call_message


class CliEndToEndTests(unittest.TestCase):
    def test_runs_read_file_then_shell_and_prints_final_answer(self):
        try:
            from mini_codex import cli
        except ImportError:
            self.fail("mini_codex.cli does not exist yet")

        read_call = read_file_call_message("project.txt", "call_read")
        shell_call = shell_call_message("pwd", "call_shell")
        final_message = type(read_call)(
            role="assistant",
            content="The project file and command result were inspected.",
            tool_calls=None,
        )
        client = FakeClient(
            [
                model_response(read_call),
                model_response(shell_call),
                model_response(final_message),
            ]
        )

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "project.txt").write_text(
                "Mini Codex CLI",
                encoding="utf-8",
            )
            output = io.StringIO()

            with (
                patch.dict(
                    os.environ,
                    {"DEEPSEEK_API_KEY": "test-key"},
                    clear=True,
                ),
                patch.object(cli, "OpenAI", return_value=client) as openai_class,
                redirect_stdout(output),
            ):
                cli.main([str(repository), "Inspect the project and run pwd"])

        openai_class.assert_called_once_with(
            api_key="test-key",
            base_url="https://api.deepseek.com",
        )
        self.assertEqual(
            output.getvalue(),
            "The project file and command result were inspected.\n",
        )
        self.assertEqual(len(client.chat.completions.requests), 3)
        self.assertEqual(
            client.chat.completions.requests[2]["messages"],
            [
                {
                    "role": "user",
                    "content": "Inspect the project and run pwd",
                },
                read_call,
                {
                    "role": "tool",
                    "tool_call_id": "call_read",
                    "content": "Mini Codex CLI",
                },
                shell_call,
                {
                    "role": "tool",
                    "tool_call_id": "call_shell",
                    "content": json.dumps(
                        {
                            "exit_code": 0,
                            "stdout": f"{repository.resolve()}\n",
                            "stderr": "",
                            "timed_out": False,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        )
        self.assertEqual(
            [
                request["model"]
                for request in client.chat.completions.requests
            ],
            ["deepseek-v4-flash"] * 3,
        )

    def test_uses_configured_base_url_and_model(self):
        from mini_codex import cli

        final_message = SimpleNamespace(
            role="assistant",
            content="Configured model answered.",
            tool_calls=None,
        )
        client = FakeClient([model_response(final_message)])

        with tempfile.TemporaryDirectory() as directory:
            output = io.StringIO()
            with (
                patch.dict(
                    os.environ,
                    {
                        "DEEPSEEK_API_KEY": "test-key",
                        "DEEPSEEK_BASE_URL": "https://deepseek.example.test",
                        "MINI_CODEX_MODEL": "test-deepseek-model",
                    },
                    clear=True,
                ),
                patch.object(cli, "OpenAI", return_value=client) as openai_class,
                redirect_stdout(output),
            ):
                cli.main([directory, "Answer directly"])

        openai_class.assert_called_once_with(
            api_key="test-key",
            base_url="https://deepseek.example.test",
        )
        self.assertEqual(
            client.chat.completions.requests[0]["model"],
            "test-deepseek-model",
        )


class CliValidationTests(unittest.TestCase):
    def test_rejects_missing_api_key_before_creating_client(self):
        from mini_codex import cli

        with tempfile.TemporaryDirectory() as directory:
            error_output = io.StringIO()
            with (
                patch.dict(os.environ, {}, clear=True),
                patch.object(cli, "OpenAI") as openai_class,
                redirect_stderr(error_output),
                self.assertRaises(BaseException) as raised,
            ):
                cli.main([directory, "Inspect the repository"])

        self.assertIsInstance(raised.exception, SystemExit)
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("DEEPSEEK_API_KEY is required", error_output.getvalue())
        openai_class.assert_not_called()

    def test_rejects_invalid_repository_before_creating_client(self):
        from mini_codex import cli

        with tempfile.TemporaryDirectory() as directory:
            missing_repository = Path(directory) / "missing"
            error_output = io.StringIO()
            with (
                patch.dict(
                    os.environ,
                    {"DEEPSEEK_API_KEY": "test-key"},
                    clear=True,
                ),
                patch.object(
                    cli,
                    "OpenAI",
                    side_effect=AssertionError("OpenAI should not be created"),
                ) as openai_class,
                redirect_stderr(error_output),
                self.assertRaises(BaseException) as raised,
            ):
                cli.main([str(missing_repository), "Inspect the repository"])

        self.assertIsInstance(raised.exception, SystemExit)
        self.assertEqual(raised.exception.code, 2)
        self.assertIn(
            "repository must be an existing directory",
            error_output.getvalue(),
        )
        openai_class.assert_not_called()

    def test_rejects_blank_task_before_creating_client(self):
        from mini_codex import cli

        with tempfile.TemporaryDirectory() as directory:
            error_output = io.StringIO()
            with (
                patch.dict(
                    os.environ,
                    {"DEEPSEEK_API_KEY": "test-key"},
                    clear=True,
                ),
                patch.object(
                    cli,
                    "OpenAI",
                    side_effect=AssertionError("OpenAI should not be created"),
                ) as openai_class,
                redirect_stderr(error_output),
                self.assertRaises(BaseException) as raised,
            ):
                cli.main([directory, "   "])

        self.assertIsInstance(raised.exception, SystemExit)
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("task must be non-empty", error_output.getvalue())
        openai_class.assert_not_called()


if __name__ == "__main__":
    unittest.main()
