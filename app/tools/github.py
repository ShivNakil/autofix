import re
from urllib.parse import urlparse

import requests


ISSUE_PATTERN = re.compile(
    r"^https?://github\.com/([^/]+)/([^/]+)/issues/(\d+)(?:/.*)?$"
)


def parse_issue_url(issue_url: str) -> tuple[str, str, int]:
    match = ISSUE_PATTERN.match(issue_url.strip())
    if not match:
        raise ValueError(
            "Unsupported GitHub issue URL. Expected "
            "https://github.com/OWNER/REPO/issues/NUMBER"
        )

    owner, repo, number = match.groups()
    return owner, repo, int(number)


def fetch_public_issue(issue_url: str) -> dict:
    owner, repo, number = parse_issue_url(issue_url)

    api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"

    response = requests.get(
        api_url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=20,
    )
    response.raise_for_status()

    data = response.json()

    if data.get("pull_request"):
        raise ValueError(
            "The supplied URL points to a Pull Request, not a GitHub Issue."
        )

    return {
        "title": data.get("title", ""),
        "description": data.get("body") or "",
        "url": data.get("html_url", issue_url),
    }
