import re
import subprocess
from pathlib import Path


def extract_patch(text: str) -> str:
    match = re.search(
        r"```(?:diff|patch)?\s*(.*?)```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()

    if text.lstrip().startswith(("diff --git", "--- ")):
        return text.strip()

    raise ValueError("The model response did not contain a diff/patch block.")


def apply_patch(repository_path: str, patch: str) -> None:
    process = subprocess.run(
        ["git", "apply", "--whitespace=fix", "-"],
        cwd=repository_path,
        input=patch,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if process.returncode != 0:
        raise RuntimeError(
            "git apply failed:\n"
            + process.stderr.strip()
        )


def validate_patch(patch: str) -> None:
    if not patch.strip():
        raise ValueError("Empty patch.")

    if "diff --git " not in patch and not (
        "--- " in patch and "+++ " in patch
    ):
        raise ValueError("Patch does not look like a unified git diff.")
