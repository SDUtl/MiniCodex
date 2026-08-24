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
