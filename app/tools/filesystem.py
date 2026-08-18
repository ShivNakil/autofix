from pathlib import Path


def read_file(
    repository_path: str,
    file_path: str,
    max_chars: int = 20000,
) -> str:
    root = Path(repository_path).resolve()
    target = (root / file_path).resolve()

    if root != target and root not in target.parents:
        raise ValueError("File access outside repository is not allowed.")

    if not target.exists():
        raise FileNotFoundError(file_path)

    if not target.is_file():
        raise ValueError(f"Not a file: {file_path}")

    text = target.read_text(
        encoding="utf-8",
        errors="replace",
    )

    if len(text) > max_chars:
        return text[:max_chars] + "\n...[TRUNCATED]..."

    return text
