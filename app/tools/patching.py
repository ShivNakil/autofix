from pathlib import Path

from app.models.edits import CodeEdit


def _normalize_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _normalize_whitespace(text: str) -> str:
    text = _normalize_line_endings(text)
    return "\n".join(
        line.rstrip() for line in text.split("\n")
    ).strip()


def _find_edit_range(content: str, old: str) -> tuple[int, int, str]:
    # 1. Exact match.
    count = content.count(old)
    if count == 1:
        start = content.index(old)
        return start, start + len(old), old

    if count > 1:
        raise ValueError(
            f"Ambiguous edit: exact target occurs {count} times."
        )

    # 2. Normalize CRLF/LF and trailing whitespace.
    normalized_old = _normalize_whitespace(old)
    normalized_content = _normalize_line_endings(content)

    candidates = []

    # Search by line windows so we can preserve the original file text while
    # tolerating CRLF and harmless trailing whitespace differences.
    content_lines = normalized_content.splitlines(keepends=True)
    old_lines = normalized_old.splitlines()

    if not old_lines:
        raise ValueError("Edit target is empty.")

    for i in range(len(content_lines) - len(old_lines) + 1):
        window = content_lines[i:i + len(old_lines)]
        window_text = "".join(window)
        window_normalized = _normalize_whitespace(window_text)

        if window_normalized == normalized_old:
            candidates.append((i, i + len(old_lines)))

    if len(candidates) == 0:
        raise ValueError(
            "Edit target was not found, even after whitespace normalization."
        )

    if len(candidates) > 1:
        raise ValueError(
            f"Ambiguous edit: whitespace-normalized target matches "
            f"{len(candidates)} locations."
        )

    start_line, end_line = candidates[0]

    # Recover exact character offsets from the original content.
    original_lines = content.splitlines(keepends=True)

    start = sum(len(x) for x in original_lines[:start_line])
    end = sum(len(x) for x in original_lines[:end_line])

    return start, end, content[start:end]


def apply_code_edit(repository_path: str, edit: CodeEdit) -> None:
    root = Path(repository_path).resolve()
    target = (root / edit.file).resolve()

    if root != target and root not in target.parents:
        raise ValueError(
            f"File access outside repository is not allowed: {edit.file}"
        )

    if not target.exists() or not target.is_file():
        raise FileNotFoundError(edit.file)

    content = target.read_text(
        encoding="utf-8",
        errors="replace",
    )

    start, end, matched_text = _find_edit_range(
        content,
        edit.old,
    )

    updated = content[:start] + edit.new + content[end:]

    target.write_text(
        updated,
        encoding="utf-8",
        newline="",
    )

    print(
        f"[EDIT] {edit.file}: matched {len(matched_text)} characters"
    )


def apply_code_edits(
    repository_path: str,
    edits: list[CodeEdit],
) -> None:
    # Validate ALL edits before modifying anything. This prevents partial
    # application of a multi-file edit plan.
    for edit in edits:
        root = Path(repository_path).resolve()
        target = (root / edit.file).resolve()

        if root != target and root not in target.parents:
            raise ValueError(
                f"File access outside repository: {edit.file}"
            )

        if not target.exists() or not target.is_file():
            raise FileNotFoundError(edit.file)

        content = target.read_text(
            encoding="utf-8",
            errors="replace",
        )

        _find_edit_range(content, edit.old)

    for edit in edits:
        apply_code_edit(repository_path, edit)
