from pathlib import Path
import pytest
from app.models.edits import CodeEdit
from app.tools.patching import apply_code_edit

def test_apply_exact_edit(tmp_path: Path):
    f = tmp_path / "calculator.py"
    f.write_text("def add(a, b):\n    return a - b\n")
    apply_code_edit(str(tmp_path), CodeEdit(
        file="calculator.py", old="return a - b",
        new="return a + b", reason="Fix addition."
    ))
    assert "return a + b" in f.read_text()

def test_reject_ambiguous_edit(tmp_path: Path):
    f = tmp_path / "example.py"
    f.write_text("x = 1\nx = 1\n")
    with pytest.raises(ValueError):
        apply_code_edit(str(tmp_path), CodeEdit(
            file="example.py", old="x = 1", new="x = 2", reason="Test."
        ))
