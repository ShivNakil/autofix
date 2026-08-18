from pathlib import Path

from app.tools.repository import get_repository_structure


def test_repository_structure(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("ignored")

    structure = get_repository_structure(str(tmp_path))

    assert "main.py" in structure
    assert ".git/config" not in structure
