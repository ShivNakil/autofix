from typing import TypedDict


class AgentState(TypedDict, total=False):
    repo_url: str
    repository_path: str
    branch_name: str

    issue_url: str
    issue_title: str
    issue_description: str

    repository_structure: str
    relevant_files: list[str]
    file_context: str

    analysis: str
    plan: str
    patch: str

    patch_applied: bool
    test_command: str
    test_output: str
    test_status: str
    tests_passed: bool

    retry_count: int
    max_retries: int

    final_status: str
    final_diff: str
    error: str
