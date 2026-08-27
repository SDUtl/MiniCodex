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
    if not repository.is_dir():
        parser.error(
            f"repository must be an existing directory: {repository}"
        )
    if not arguments.task.strip():
        parser.error("task must be non-empty")

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        parser.error("DEEPSEEK_API_KEY is required")

    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    answer = run_agent_loop(
        arguments.task,
        repository,
        model=os.getenv("MINI_CODEX_MODEL", "deepseek-v4-flash"),
        client=client,
    )
    print(answer)
