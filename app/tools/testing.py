import subprocess
from pathlib import Path

from app.models.test_result import TestResult, TestStatus


def _has_pytest_files(root: Path) -> bool:
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


def classify_test_output(output: str, return_code: int) -> TestStatus:
    if return_code == 0:
        return TestStatus.PASSED

    text = output.lower()

    environment_markers = (
        "no module named",
        "modulenotfounderror",
        "cannot find module",
        "command not found",
        "is not recognized as an internal or external command",
        "no such file or directory",
        "could not find or load main class",
        "dependency resolution failed",
        "failed to resolve dependencies",
        "npm err! code enotfound",
        "npm err! code etarget",
    )

    timeout_markers = (
        "test_timeout",
        "timed out",
        "timeout expired",
    )

    if any(marker in text for marker in timeout_markers):
        return TestStatus.TIMEOUT

    if any(marker in text for marker in environment_markers):
        return TestStatus.ENVIRONMENT_ERROR

    # A non-zero test runner exit code with actual assertion/test failure
    # output is treated as a code failure so the debugging agent can inspect it.
    if (
        "failed" in text
        or "failure" in text
        or "assertionerror" in text
        or "assert " in text
        or "error:" in text
    ):
        return TestStatus.CODE_FAILURE

    return TestStatus.UNKNOWN_FAILURE


def run_tests(
    repository_path: str,
    command: str | None = None,
    timeout: int = 120,
) -> TestResult:
    command = command or detect_test_command(repository_path)

    if not command:
        return TestResult(
            status=TestStatus.ENVIRONMENT_ERROR,
            output="NO_TEST_COMMAND_DETECTED",
            command="",
        )

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

        output = (result.stdout + "\n" + result.stderr)[-30000:]
        status = classify_test_output(output, result.returncode)

        return TestResult(
            status=status,
            output=output,
            command=command,
        )

    except subprocess.TimeoutExpired:
        return TestResult(
            status=TestStatus.TIMEOUT,
            output=f"TEST_TIMEOUT after {timeout} seconds",
            command=command,
        )
