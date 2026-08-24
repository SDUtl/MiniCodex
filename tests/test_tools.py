import importlib
import json
import tempfile
import unittest
from pathlib import Path


class ReadFileSchemaTests(unittest.TestCase):
    def test_describes_read_file_and_its_path_parameter(self):
        try:
            tools = importlib.import_module("mini_codex.tools")
        except ModuleNotFoundError:
            self.fail("mini_codex.tools does not exist yet")

        self.assertEqual(
            tools.READ_FILE_TOOL,
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a UTF-8 text file from the repository.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path relative to the repository root.",
                            }
                        },
                        "required": ["path"],
                        "additionalProperties": False,
                    },
                },
            },
        )


class ShellSchemaTests(unittest.TestCase):
    def test_describes_shell_and_its_command_parameter(self):
        tools = importlib.import_module("mini_codex.tools")
        self.assertTrue(
            hasattr(tools, "SHELL_TOOL"),
            "mini_codex.tools.SHELL_TOOL does not exist yet",
        )
        self.assertEqual(
            tools.SHELL_TOOL,
            {
                "type": "function",
                "function": {
                    "name": "shell",
                    "description": "Run a shell command in the repository.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "Shell command to execute.",
                            }
                        },
                        "required": ["command"],
                        "additionalProperties": False,
                    },
                },
            },
        )


class ShellTests(unittest.TestCase):
    def test_runs_command_in_repository_and_returns_json(self):
        tools = importlib.import_module("mini_codex.tools")
        self.assertTrue(
            hasattr(tools, "shell"),
            "mini_codex.tools.shell does not exist yet",
        )

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            result = json.loads(tools.shell(repository, "pwd"))

        self.assertEqual(
            result,
            {
                "exit_code": 0,
                "stdout": f"{repository.resolve()}\n",
                "stderr": "",
                "timed_out": False,
            },
        )

    def test_returns_nonzero_exit_as_observation(self):
        tools = importlib.import_module("mini_codex.tools")

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            try:
                result = json.loads(
                    tools.shell(
                        repository,
                        "printf 'output'; printf 'problem' >&2; exit 7",
                    )
                )
            except Exception as error:
                self.fail(f"shell failure should be an observation: {error}")

        self.assertEqual(
            result,
            {
                "exit_code": 7,
                "stdout": "output",
                "stderr": "problem",
                "timed_out": False,
            },
        )

    def test_returns_invalid_command_as_observation(self):
        tools = importlib.import_module("mini_codex.tools")
        expected = {
            "exit_code": None,
            "stdout": "",
            "stderr": "Error: command must be a non-empty string",
            "timed_out": False,
        }

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            for command in (None, 42, "", "   "):
                with self.subTest(command=command):
                    try:
                        result = json.loads(tools.shell(repository, command))
                    except Exception as error:
                        self.fail(f"invalid command should be an observation: {error}")

                    self.assertEqual(result, expected)

    def test_returns_timeout_as_observation(self):
        tools = importlib.import_module("mini_codex.tools")

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            result = json.loads(
                tools.shell(
                    repository,
                    "printf 'before timeout'; sleep 0.2",
                    timeout_seconds=0.02,
                )
            )

        self.assertEqual(
            result,
            {
                "exit_code": None,
                "stdout": "before timeout",
                "stderr": "",
                "timed_out": True,
            },
        )


class ReadFileTests(unittest.TestCase):
    def test_reads_utf8_text_file_from_repository(self):
        tools = importlib.import_module("mini_codex.tools")
        self.assertTrue(
            hasattr(tools, "read_file"),
            "mini_codex.tools.read_file does not exist yet",
        )

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "notes.txt").write_text("Harness 工程", encoding="utf-8")

            result = tools.read_file(repository, "notes.txt")

        self.assertEqual(result, "Harness 工程")

    def test_returns_error_when_file_does_not_exist(self):
        tools = importlib.import_module("mini_codex.tools")

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            try:
                result = tools.read_file(repository, "missing.txt")
            except FileNotFoundError:
                self.fail("read_file should return an observation instead of raising")

        self.assertEqual(result, "Error: file not found: missing.txt")

    def test_returns_error_when_path_is_empty(self):
        tools = importlib.import_module("mini_codex.tools")

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            try:
                result = tools.read_file(repository, "")
            except IsADirectoryError:
                self.fail("read_file should reject an empty path before reading")

        self.assertEqual(result, "Error: path must be a non-empty string")

    def test_rejects_path_outside_repository(self):
        tools = importlib.import_module("mini_codex.tools")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "repository"
            repository.mkdir()
            (root / "secret.txt").write_text("outside", encoding="utf-8")

            result = tools.read_file(repository, "../secret.txt")

        self.assertEqual(
            result,
            "Error: path must stay within repository: ../secret.txt",
        )


if __name__ == "__main__":
    unittest.main()
