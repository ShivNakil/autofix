from tqdm import tqdm
import argparse
import sys

from app.config import settings
from app.tools.github import fetch_public_issue
from app.workflow.graph import build_graph


def parse_args():
    parser = argparse.ArgumentParser(
        description="AutoFix Agent Phase 1"
    )

    parser.add_argument("--repo", help="GitHub repository URL")
    parser.add_argument("--issue-url", default="")
    parser.add_argument("--issue-title")
    parser.add_argument("--issue-description")
    parser.add_argument(
        "--max-retries",
        type=int,
        default=settings.max_retries,
    )

    return parser.parse_args()


def prompt_if_missing(value: str | None, message: str) -> str:
    if value:
        return value
    return input(message).strip()


def run_with_progress(graph, initial_state, max_retries):
    labels = {
        "clone": "Cloning repository",
        "inspect": "Inspecting repository",
        "analysis": "Analyzing issue",
        "patch": "Applying fix",
        "test": "Running tests",
        "debug": "Debugging failure",
        "finish": "Finalizing",
    }

    with tqdm(
        total=6 + (max_retries * 2),
        desc="AutoFix | Starting",
        unit="step",
        dynamic_ncols=True,
        leave=True,
    ) as bar:
        final_state = dict(initial_state)

        for event in graph.stream(initial_state, stream_mode="updates"):
            for node_name, node_state in event.items():
                if isinstance(node_state, dict):
                    final_state.update(node_state)

                if node_name == "debug":
                    retry = final_state.get("retry_count", 0)
                    label = f"Debugging failure ({retry}/{max_retries})"
                else:
                    label = labels.get(node_name, node_name)

                bar.set_description(f"AutoFix | {label}")
                bar.update(1)

        bar.set_description("AutoFix | Complete")

    return final_state

def main():
    args = parse_args()

    repo = prompt_if_missing(
        args.repo,
        "GitHub repository URL: ",
    )

    issue_url = args.issue_url or input(
        "GitHub issue URL (optional): "
    ).strip()

    # If an issue URL is provided, retrieve the issue directly from GitHub.
    # Title/description flags can still override the fetched values.
    fetched_issue = {}
    if issue_url:
        try:
            fetched_issue = fetch_public_issue(issue_url)
            print(f"Fetched GitHub issue: {fetched_issue['title']}")
        except Exception as exc:
            print(f"Could not fetch GitHub issue: {exc}")
            print("You can continue by entering the issue manually.")

    title = args.issue_title or fetched_issue.get("title") or input(
        "Issue title: "
    ).strip()

    description = (
        args.issue_description
        or fetched_issue.get("description")
        or input("Issue description: ").strip()
    )

    print("\nStarting AutoFix Agent...")
    print(f"Provider : {settings.llm_provider}")
    print(f"Model    : {settings.llm_model}")
    print(f"Repo     : {repo}")
    print(f"Retries  : {args.max_retries}\n")

    graph = build_graph()

    try:
        result = run_with_progress(
            graph,
            {
                "repo_url": repo,
                "issue_url": issue_url,
                "issue_title": title,
                "issue_description": description,
                "retry_count": 0,
                "max_retries": args.max_retries,
                "final_status": "STARTED",
            },
            args.max_retries,
        )
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print("\n" + "=" * 70)
    print("FINAL STATUS:", result.get("final_status"))
    print("=" * 70)

    print("\n--- ANALYSIS ---")
    print(result.get("analysis", ""))

    print("\n--- TEST COMMAND ---")
    print(result.get("test_command", "None"))

    print("\n--- TEST OUTPUT ---")
    print(result.get("test_output", "")[-10000:])

    print("\n--- GIT DIFF ---")
    print(result.get("final_diff", ""))

    print("\nRepository:")
    print(result.get("repository_path", ""))

    print("\nBranch:")
    print(result.get("branch_name", ""))


if __name__ == "__main__":
    main()
