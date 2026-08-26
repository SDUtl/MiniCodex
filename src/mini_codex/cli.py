import argparse
import os
from pathlib import Path

from openai import OpenAI

from mini_codex.agent import run_agent_loop


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="mini-codex")
    parser.add_argument("repository")
    parser.add_argument("task")
    arguments = parser.parse_args(argv)

    repository = Path(arguments.repository).resolve()
    client = OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    answer = run_agent_loop(
        arguments.task,
        repository,
        model=os.getenv("MINI_CODEX_MODEL", "deepseek-v4-flash"),
        client=client,
    )
    print(answer)
