import importlib
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
