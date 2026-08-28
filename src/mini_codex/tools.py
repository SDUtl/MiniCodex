import json
import subprocess
from pathlib import Path


READ_FILE_TOOL = {
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
}

SHELL_TOOL = {
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
}


def read_file(repository: Path, path: str) -> str:
    if not isinstance(path, str) or not path:
        return "Error: path must be a non-empty string"

    repository = repository.resolve()
    target = (repository / path).resolve()
    try:
        target.relative_to(repository)
    except ValueError:
        return f"Error: path must stay within repository: {path}"

    try:
        return target.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"Error: file not found: {path}"


def shell(repository: Path, command: str, timeout_seconds: float = 10) -> str:
    if not isinstance(command, str) or not command.strip():
        return json.dumps(
            {
                "exit_code": None,
                "stdout": "",
                "stderr": "Error: command must be a non-empty string",
                "timed_out": False,
            },
            ensure_ascii=False,
        )

    try:
        completed = subprocess.run(
            command,
            cwd=repository.resolve(),
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        # check = false 把失败信息传给模型

    except subprocess.TimeoutExpired as error:
        # TimeoutExpired 的部分输出即使开启 text=True，也可能仍然是 bytes。
        stdout = error.stdout or ""
        stderr = error.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
            # 序列化为字符串
        return json.dumps(
            {
                "exit_code": None,
                "stdout": stdout,
                "stderr": stderr,
                "timed_out": True,
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "timed_out": False,
        },
        ensure_ascii=False,
    )
