import importlib
import unittest
from types import SimpleNamespace


class FakeChatCompletions:
    def __init__(self, content=""):
        self.last_request = None
        self.content = content

    def create(self, **request):
        self.last_request = request
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeChat:
    def __init__(self, content=""):
        self.completions = FakeChatCompletions(content)


class FakeClient:
    def __init__(self, content=""):
        self.chat = FakeChat(content)


class GenerateOnceTests(unittest.TestCase):
    def test_sends_prompt_and_model_to_chat_completions_api(self):
        try:
            llm = importlib.import_module("mini_codex.llm")
        except ModuleNotFoundError:
            self.fail("mini_codex.llm does not exist yet")

        client = FakeClient()

        llm.generate_once(
            "Explain what an agent loop is.",
            model="test-model",
            client=client,
        )

        self.assertEqual(
            client.chat.completions.last_request,
            {
                "model": "test-model",
                "messages": [
                    {
                        "role": "user",
                        "content": "Explain what an agent loop is.",
                    }
                ],
            },
        )

    def test_returns_assistant_message_content(self):
        llm = importlib.import_module("mini_codex.llm")
        client = FakeClient(content="An agent loop repeats act and observe.")

        result = llm.generate_once(
            "Explain what an agent loop is.",
            model="test-model",
            client=client,
        )

        self.assertEqual(result, "An agent loop repeats act and observe.")


if __name__ == "__main__":
    unittest.main()
