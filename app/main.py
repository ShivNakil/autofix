from tqdm import tqdm
import argparse
import sys

from app.config import settings
from app.tools.github import parse_repo_url, fetch_open_issues
from app.workflow.graph import build_graph


def parse_args():
    parser = argparse.ArgumentParser(
        description="AutoFix Agent Phase 1"
    )

    parser.add_argument("--repo", help="GitHub repository URL")
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

    # Parse the repository URL to get owner and repo
    try:
        owner, repo_name = parse_repo_url(repo)
    except ValueError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    # Fetch open issues
    print(f"\nFetching open issues from {owner}/{repo_name}...")
    try:
        issues = fetch_open_issues(owner, repo_name)
    except Exception as exc:
        print(f"Failed to fetch issues: {exc}")
        sys.exit(1)

    if not issues:
        print("No open issues found in the repository.")
        sys.exit(0)

    # Display issues for user selection
    print("\nOpen issues:")
    for idx, issue in enumerate(issues, start=1):
        # Truncate title if too long for display
        title = issue["title"]
        if len(title) > 60:
            title = title[:57] + "..."
        print(f"  {idx}. #{issue['number']}: {title}")

    # Ask user to select an issue
    while True:
        try:
            choice = input("\nSelect an issue by number (or 0 to cancel): ").strip()
            if choice == "0":
                print("Cancelled.")
                sys.exit(0)
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(issues):
                selected_issue = issues[choice_idx]
                break
            else:
                print(f"Please enter a number between 1 and {len(issues)}.")
        except ValueError:
            print("Please enter a valid number.")

    title = selected_issue["title"]
    description = selected_issue["description"]
    issue_url = selected_issue["html_url"]

    print(f"\nSelected issue: #{selected_issue['number']} - {title}")

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