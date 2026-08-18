import subprocess
from pathlib import Path


def detect_test_command(repository_path: str) -> str | None:
    root = Path(repository_path)

    if (root / "pytest.ini").exists() or (root / "pyproject.toml").exists() \
            or (root / "pytest.ini").exists() \
            or (root / "tests").is_dir():
        if (root / "pytest.ini").exists() or (root / "tests").is_dir():
            return "python -m pytest"

    if (root / "package.json").exists():
        return "npm test"

    if (root / "go.mod").exists():
        return "go test ./..."

    if (root / "pom.xml").exists():
        return "mvn test"

    return None


def run_tests(
    repository_path: str,
    command: str | None = None,
    timeout: int = 120,
) -> tuple[bool, str]:
    command = command or detect_test_command(repository_path)

    if not command:
        return False, "NO_TEST_COMMAND_DETECTED"

    try:
        result = subprocess.run(
            command,
            cwd=repository_path,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )

        output = result.stdout + "\n" + result.stderr

        return result.returncode == 0, output[-30000:]

    except subprocess.TimeoutExpired:
        return False, f"TEST_TIMEOUT after {timeout} seconds"
