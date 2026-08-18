import subprocess
from pathlib import Path


def run_git(args: list[str], cwd: str | Path | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed:\n{result.stderr.strip()}"
        )
    return result.stdout.strip()


def clone_repository(repo_url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    run_git(["clone", "--depth", "1", repo_url, str(destination)])


def create_branch(repository_path: str, branch_name: str) -> None:
    run_git(["checkout", "-b", branch_name], cwd=repository_path)


def get_diff(repository_path: str) -> str:
    return run_git(["diff", "--"], cwd=repository_path)


def get_status(repository_path: str) -> str:
    return run_git(["status", "--short"], cwd=repository_path)
