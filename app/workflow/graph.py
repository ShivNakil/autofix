from pathlib import Path

from langgraph.graph import StateGraph, START, END

from app.agents.coding_agent import analyze, generate_patch, debug_patch
from app.config import settings
from app.models.state import AgentState
from app.tools.filesystem import read_file
from app.tools.git import clone_repository, create_branch, get_diff
from app.tools.patching import apply_patch, extract_patch, validate_patch
from app.tools.repository import (
    get_repository_structure,
    search_repository,
)
from app.tools.testing import detect_test_command, run_tests


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


def patch_node(state: AgentState) -> AgentState:
    if state.get("tests_passed"):
        return state

    raw = generate_patch(
        state["issue_title"],
        state["issue_description"],
        state["analysis"],
        state.get("file_context", ""),
    )

    if "NO_SAFE_PATCH" in raw:
        return {
            **state,
            "patch": "",
            "patch_applied": False,
            "final_status": "NO_SAFE_PATCH",
        }

    patch = extract_patch(raw)
    validate_patch(patch)
    apply_patch(state["repository_path"], patch)

    return {
        **state,
        "patch": patch,
        "patch_applied": True,
    }


def test_node(state: AgentState) -> AgentState:
    command = detect_test_command(state["repository_path"])
    passed, output = run_tests(
        state["repository_path"],
        command=command,
        timeout=settings.test_timeout_seconds,
    )

    return {
        **state,
        "test_command": command or "",
        "test_output": output,
        "tests_passed": passed,
    }


def should_debug(state: AgentState) -> str:
    if state.get("tests_passed"):
        return "finish"

    if state.get("final_status") == "NO_SAFE_PATCH":
        return "finish"

    if state.get("iteration", 0) >= state.get(
        "max_iterations",
        settings.max_iterations,
    ):
        return "finish"

    return "debug"


def debug_node(state: AgentState) -> AgentState:
    # Re-read the relevant files after the failed attempt.
    file_context = state.get("file_context", "")

    raw = debug_patch(
        state["issue_title"],
        state["issue_description"],
        state["analysis"],
        state.get("test_output", ""),
        file_context,
    )

    if "NO_SAFE_PATCH" in raw:
        return {
            **state,
            "patch": "",
            "patch_applied": False,
            "final_status": "NO_SAFE_PATCH",
        }

    patch = extract_patch(raw)
    validate_patch(patch)

    # A failed patch may have changed the tree. For Phase 1 we attempt the
    # correction directly; git apply will reject incompatible hunks.
    apply_patch(state["repository_path"], patch)

    return {
        **state,
        "patch": patch,
        "patch_applied": True,
        "iteration": state.get("iteration", 0) + 1,
    }


def finish_node(state: AgentState) -> AgentState:
    if state.get("tests_passed"):
        status = "SUCCESS"
    elif state.get("final_status") == "NO_SAFE_PATCH":
        status = "NO_SAFE_PATCH"
    else:
        status = "FAILED"

    return {
        **state,
        "final_status": status,
        "final_diff": get_diff(state["repository_path"]),
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
