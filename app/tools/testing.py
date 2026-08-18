import subprocess
from pathlib import Path


def _has_pytest_files(root: Path) -> bool:
    """Detect common pytest test-file conventions."""
    if any(root.glob("test_*.py")):
        return True
    if any(root.glob("*_test.py")):
        return True

    tests_dir = root / "tests"
    if tests_dir.is_dir():
        if any(tests_dir.rglob("test_*.py")):
            return True
        if any(tests_dir.rglob("*_test.py")):
            return True

    return False


def detect_test_command(repository_path: str) -> str | None:
    root = Path(repository_path)

    # Python repositories often keep tests directly beside the source file,
    # e.g. calculator.py + test_calculator.py. Do not require a tests/ folder.
    if _has_pytest_files(root):
        return "python -m pytest"

    if (root / "pytest.ini").exists():
        return "python -m pytest"

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text(
                encoding="utf-8",
                errors="replace",
            ).lower()
            if "pytest" in content:
                return "python -m pytest"
        except OSError:
            pass

    if (root / "package.json").exists():
        return "npm test"

    if (root / "go.mod").exists():
        return "go test ./..."

    if (root / "pom.xml").exists():
        return "mvn test"

    if (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        return "gradlew test"

    return None


def run_tests(
    repository_path: str,
    command: str | None = None,
    timeout: int = 120,
) -> tuple[bool, str]:
    command = command or detect_test_command(repository_path)

    if not command:
        return False, "NO_TEST_COMMAND_DETECTED"

    print(f"[TEST] Executing: {command}")

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
