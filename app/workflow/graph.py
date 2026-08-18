from pathlib import Path

from langgraph.graph import StateGraph, START, END

from app.agents.coding_agent import analyze, generate_edits, debug_edits
from app.config import settings
from app.models.state import AgentState
from app.tools.filesystem import read_file
from app.tools.git import clone_repository, create_branch, get_diff
from app.tools.patching import apply_code_edits
from app.tools.repository import (
    get_repository_structure,
    search_repository,
)
from app.tools.testing import detect_test_command, run_tests
from app.models.test_result import TestStatus



def _build_file_context(repository_path: str, files: list[str]) -> str:
    """Read the current contents of relevant files after every edit."""
    chunks = []

    for relative in files[:12]:
        try:
            content = read_file(
                repository_path,
                relative,
                max_chars=12000,
            )
            chunks.append(
                f"===== FILE: {relative} =====\n{content}"
            )
        except Exception:
            continue

    return "\n\n".join(chunks)


def clone_node(state: AgentState) -> AgentState:
    repo_url = state["repo_url"]
    workspace = settings.workspace_path
    workspace.mkdir(parents=True, exist_ok=True)

    repo_name = repo_url.rstrip("/").split("/")[-1]
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]

    destination = workspace / repo_name

    if destination.exists():
        raise RuntimeError(
            f"Workspace already exists: {destination}. "
            "Delete it or use a different repository."
        )

    clone_repository(repo_url, destination)

    branch = f"autofix/issue-{state.get('iteration', 0)}"
    create_branch(str(destination), branch)

    return {
        **state,
        "repository_path": str(destination),
        "branch_name": branch,
    }


def inspect_node(state: AgentState) -> AgentState:
    structure = get_repository_structure(
        state["repository_path"],
        max_files=600,
    )

    terms = (
        state["issue_title"].split()
        + state["issue_description"].split()
    )

    terms = [
        word.strip(".,:;!?()[]{}\"'`").lower()
        for word in terms
        if len(word.strip(".,:;!?()[]{}\"'`")) >= 4
    ][:20]

    matches = search_repository(
        state["repository_path"],
        terms,
        max_matches=60,
    )

    relevant_files = []
    for match in matches:
        path = match.split(":", 1)[0]
        if path not in relevant_files:
            relevant_files.append(path)

    # Keep a small amount of source context for Phase 1.
    file_chunks = []
    for relative in relevant_files[:12]:
        try:
            content = read_file(
                state["repository_path"],
                relative,
                max_chars=12000,
            )
            file_chunks.append(
                f"===== FILE: {relative} =====\n{content}"
            )
        except Exception:
            continue

    return {
        **state,
        "repository_structure": structure,
        "relevant_files": relevant_files,
        "file_context": "\n\n".join(file_chunks),
    }


def analysis_node(state: AgentState) -> AgentState:
    analysis = analyze(
        state["issue_title"],
        state["issue_description"],
        state["repository_structure"],
        "\n".join(
            search_repository(
                state["repository_path"],
                state["issue_title"].split(),
                max_matches=40,
            )
        ),
        state.get("file_context", ""),
    )

    return {
        **state,
        "analysis": analysis,
    }


def apply_edits(state: AgentState, plan) -> AgentState:
    if not plan.edits:
        print("[EDIT] Model returned no safe edits.")
        return {
            **state,
            "patch_applied": False,
            "final_status": "NO_SAFE_EDIT",
        }

    print(f"[EDIT] Received {len(plan.edits)} proposed edit(s).")

    apply_code_edits(
        state["repository_path"],
        plan.edits,
    )

    # Refresh the actual current file contents after modification.
    files = state.get("relevant_files", [])
    refreshed = _build_file_context(
        state["repository_path"],
        files,
    )

    return {
        **state,
        "patch_applied": True,
        "file_context": refreshed,
    }


def patch_node(state: AgentState) -> AgentState:
    if state.get("tests_passed"):
        return state
    return apply_edits(state, generate_edits(
        state["issue_title"], state["issue_description"],
        state["analysis"], state.get("file_context", "")
    ))

def test_node(state: AgentState) -> AgentState:
    command = detect_test_command(state["repository_path"])

    if not command:
        print("[TEST] No test command detected.")
        return {
            **state,
            "test_command": "",
            "test_output": "NO_TEST_COMMAND_DETECTED",
            "test_status": TestStatus.ENVIRONMENT_ERROR.value,
            "tests_passed": False,
            "final_status": "ENVIRONMENT_ERROR",
        }

    print(f"[TEST] Running: {command}")

    result = run_tests(
        state["repository_path"],
        command=command,
        timeout=settings.test_timeout_seconds,
    )

    print(f"[TEST] STATUS: {result.status.value}")

    return {
        **state,
        "test_command": result.command,
        "test_output": result.output,
        "test_status": result.status.value,
        "tests_passed": result.status == TestStatus.PASSED,
        "final_status": (
            "SUCCESS"
            if result.status == TestStatus.PASSED
            else (
                "ENVIRONMENT_ERROR"
                if result.status == TestStatus.ENVIRONMENT_ERROR
                else (
                    "TIMEOUT"
                    if result.status == TestStatus.TIMEOUT
                    else state.get("final_status", "")
                )
            )
        ),
    }

def should_debug(state: AgentState) -> str:
    status = state.get("test_status")

    if status == TestStatus.PASSED.value:
        return "finish"

    if status in {
        TestStatus.ENVIRONMENT_ERROR.value,
        TestStatus.TIMEOUT.value,
    }:
        return "finish"

    if state.get("final_status") == "NO_SAFE_EDIT":
        return "finish"

    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", settings.max_retries)

    if retry_count >= max_retries:
        return "finish"

    return "debug"

def debug_node(state: AgentState) -> AgentState:
    retry_count = state.get("retry_count", 0) + 1
    max_retries = state.get("max_retries", settings.max_retries)

    print(f"[DEBUG] Retry {retry_count}/{max_retries}")

    refreshed = _build_file_context(
        state["repository_path"],
        state.get("relevant_files", []),
    )

    current_state = {
        **state,
        "file_context": refreshed,
        "retry_count": retry_count,
    }

    plan = debug_edits(
        current_state["issue_title"],
        current_state["issue_description"],
        current_state["analysis"],
        current_state.get("test_output", ""),
        current_state.get("file_context", ""),
    )

    return apply_edits(current_state, plan)

def get_clean_diff(repository_path: str) -> str:
    """Return Git diff without generated artifacts."""
    ignored_prefixes = (
        "__pycache__/", ".pytest_cache/", ".venv/", "venv/",
        "node_modules/", ".mypy_cache/", ".ruff_cache/"
    )
    ignored_suffixes = (".pyc", ".pyo", ".class")

    raw = get_diff(repository_path)
    if not raw:
        return ""

    out = []
    skip = False
    for line in raw.splitlines(keepends=True):
        if line.startswith("diff --git "):
            parts = line.strip().split()
            path = parts[2][2:] if len(parts) >= 4 and parts[2].startswith("a/") else ""
            path = path.replace("\\", "/")
            skip = path.startswith(ignored_prefixes) or path.endswith(ignored_suffixes)
        if not skip:
            out.append(line)
    return "".join(out)


def finish_node(state: AgentState) -> AgentState:
    test_status = state.get("test_status")

    if test_status == TestStatus.PASSED.value:
        status = "SUCCESS"
        print("[RESULT] SUCCESS - tests passed.")
    elif test_status == TestStatus.ENVIRONMENT_ERROR.value:
        status = "ENVIRONMENT_ERROR"
        print("[RESULT] STOPPED - test environment is not ready.")
    elif test_status == TestStatus.TIMEOUT.value:
        status = "TIMEOUT"
        print("[RESULT] STOPPED - tests timed out.")
    elif state.get("final_status") == "NO_SAFE_EDIT":
        status = "NO_SAFE_EDIT"
        print("[RESULT] STOPPED - no safe edit was generated.")
    else:
        status = "FAILED"
        print("[RESULT] FAILED - code tests did not pass.")

    return {
        **state,
        "final_status": status,
        "final_diff": get_clean_diff(state["repository_path"]),
    }

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("clone", clone_node)
    graph.add_node("inspect", inspect_node)
    graph.add_node("analysis", analysis_node)
    graph.add_node("patch", patch_node)
    graph.add_node("test", test_node)
    graph.add_node("debug", debug_node)
    graph.add_node("finish", finish_node)

    graph.add_edge(START, "clone")
    graph.add_edge("clone", "inspect")
    graph.add_edge("inspect", "analysis")
    graph.add_edge("analysis", "patch")
    graph.add_edge("patch", "test")

    graph.add_conditional_edges(
        "test",
        should_debug,
        {
            "debug": "debug",
            "finish": "finish",
        },
    )

    graph.add_edge("debug", "test")
    graph.add_edge("finish", END)

    return graph.compile()
