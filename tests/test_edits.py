from pathlib import Path

import pytest

from app.models.edits import CodeEdit
from app.tools.patching import apply_code_edit


def test_apply_exact_edit(tmp_path: Path):
    f = tmp_path / "calculator.py"
    f.write_text("def add(a, b):\n    return a - b\n")

    apply_code_edit(
        str(tmp_path),
        CodeEdit(
            file="calculator.py",
            old="return a - b",
            new="return a + b",
            reason="Fix addition.",
        ),
    )

    assert "return a + b" in f.read_text()


def test_apply_multiline_edit_with_trailing_whitespace(tmp_path: Path):
    f = tmp_path / "calculator.py"
    f.write_text(
        "def subtract(a, b):\r\n"
        "    return a * b   \r\n"
    )

    apply_code_edit(
        str(tmp_path),
        CodeEdit(
            file="calculator.py",
            old="def subtract(a, b):\n"
                "    return a * b",
            new="def subtract(a, b):\n"
                 "    return a - b",
            reason="Fix subtraction.",
        ),
    )

    assert "return a - b" in f.read_text()


def test_reject_ambiguous_edit(tmp_path: Path):
    f = tmp_path / "example.py"
    f.write_text("x = 1\nx = 1\n")

    with pytest.raises(ValueError, match="Ambiguous"):
        apply_code_edit(
            str(tmp_path),
            CodeEdit(
                file="example.py",
                old="x = 1",
                new="x = 2",
                reason="Test.",
            ),
        )


def test_reject_test_file_edit(tmp_path: Path):
    test_file = tmp_path / "test_calculator.py"
    test_file.write_text("def test_x():\n    assert True\n")

    with pytest.raises(ValueError, match="test-file"):
        from app.tools.patching import apply_code_edits
        apply_code_edits(
            str(tmp_path),
            [CodeEdit(
                file="test_calculator.py",
                old="assert True",
                new="assert False",
                reason="Should never be allowed in Phase 1.",
            )],
        )
