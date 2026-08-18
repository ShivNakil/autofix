from enum import Enum
from dataclasses import dataclass


class TestStatus(str, Enum):
    PASSED = "passed"
    CODE_FAILURE = "code_failure"
    ENVIRONMENT_ERROR = "environment_error"
    TIMEOUT = "timeout"
    UNKNOWN_FAILURE = "unknown_failure"


@dataclass
class TestResult:
    status: TestStatus
    output: str
    command: str
