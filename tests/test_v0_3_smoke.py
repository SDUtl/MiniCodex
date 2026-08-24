import importlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tests.test_agent import FakeClient, model_response, read_file_call_message


class V03SmokeTests(unittest.TestCase):
    def test_prints_the_complete_tool_call_round_trip(self):
        try:
            smoke = importlib.import_module("examples.v0_3_deepseek_smoke")
        except ModuleNotFoundError:
            self.fail("examples.v0_3_deepseek_smoke does not exist yet")

        first_message = read_file_call_message()
        final_message = SimpleNamespace(content="The heading is Mini Codex.")
        client = FakeClient(
            [model_response(first_message), model_response(final_message)]
        )
        output = []

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "README.md").write_text("# Mini Codex", encoding="utf-8")

            result = smoke.run_smoke(
                client=client,
                repository=repository,
                model="test-model",
                emit=output.append,
            )

        self.assertEqual(result, "The heading is Mini Codex.")
        self.assertEqual(
            output,
            [
                "MODEL CALL 1",
                "tool_choice: required",
                "tool call: read_file",
                'arguments: {"path": "README.md"}',
                "tool_call_id: call_readme",
                "MODEL CALL 2",
                "tool_choice: none",
                "tool result for call_readme:",
                "# Mini Codex",
                "assistant content:",
                "The heading is Mini Codex.",
                "FINAL ANSWER",
                "The heading is Mini Codex.",
            ],
        )


if __name__ == "__main__":
    unittest.main()
