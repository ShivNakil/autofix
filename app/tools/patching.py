from pathlib import Path
from app.models.edits import CodeEdit

def apply_code_edit(repository_path: str, edit: CodeEdit) -> None:
    root = Path(repository_path).resolve()
    target = (root / edit.file).resolve()
    if root != target and root not in target.parents:
        raise ValueError("File access outside repository is not allowed.")
    if not target.exists() or not target.is_file():
        raise FileNotFoundError(edit.file)
    content = target.read_text(encoding="utf-8", errors="replace")
    count = content.count(edit.old)
    if count == 0:
        raise ValueError(f"Exact target text was not found in {edit.file}.")
    if count > 1:
        raise ValueError(f"Exact target text occurs {count} times in {edit.file}; refusing ambiguous edit.")
    target.write_text(content.replace(edit.old, edit.new, 1), encoding="utf-8")

def apply_code_edits(repository_path: str, edits: list[CodeEdit]) -> None:
    root = Path(repository_path).resolve()
    for edit in edits:
        target = (root / edit.file).resolve()
        if root != target and root not in target.parents:
            raise ValueError(f"File access outside repository: {edit.file}")
        if not target.exists() or not target.is_file():
            raise FileNotFoundError(edit.file)
        content = target.read_text(encoding="utf-8", errors="replace")
        if content.count(edit.old) != 1:
            raise ValueError(f"Expected exactly one match for edit in {edit.file}, found {content.count(edit.old)}.")
    for edit in edits:
        apply_code_edit(repository_path, edit)
