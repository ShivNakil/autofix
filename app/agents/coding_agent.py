from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.prompts import (
    ANALYSIS_PROMPT,
    PATCH_PROMPT,
    DEBUG_PROMPT,
)
from app.llm.factory import get_llm


def _text(response) -> str:
    content = response.content
    if isinstance(content, str):
        return content
    return str(content)


def analyze(
    issue_title: str,
    issue_description: str,
    repository_structure: str,
    search_results: str,
    file_context: str,
) -> str:
    llm = get_llm()

    user = f"""
ISSUE TITLE:
{issue_title}

ISSUE DESCRIPTION:
{issue_description}

REPOSITORY STRUCTURE:
{repository_structure}

SEARCH RESULTS:
{search_results}

RELEVANT FILE CONTENT:
{file_context}
"""

    response = llm.invoke([
        SystemMessage(content=ANALYSIS_PROMPT),
        HumanMessage(content=user),
    ])

    raw = _text(response)

    print("\n========== RAW GEMINI PATCH ==========")
    print(raw)
    print("========== END RAW GEMINI PATCH ==========\n")

    return raw


def generate_patch(
    issue_title: str,
    issue_description: str,
    analysis: str,
    file_context: str,
) -> str:
    llm = get_llm()

    user = f"""
ISSUE TITLE:
{issue_title}

ISSUE DESCRIPTION:
{issue_description}

ENGINEERING ANALYSIS:
{analysis}

RELEVANT FILE CONTENT:
{file_context}
"""

    response = llm.invoke([
        SystemMessage(content=PATCH_PROMPT),
        HumanMessage(content=user),
    ])

    raw = _text(response)

    print("\n========== RAW GEMINI PATCH ==========")
    print(raw)
    print("========== END RAW GEMINI PATCH ==========\n")

    return raw


def debug_patch(
    issue_title: str,
    issue_description: str,
    analysis: str,
    test_output: str,
    file_context: str,
) -> str:
    llm = get_llm()

    user = f"""
ISSUE TITLE:
{issue_title}

ISSUE DESCRIPTION:
{issue_description}

PREVIOUS ANALYSIS:
{analysis}

TEST FAILURE:
{test_output}

RELEVANT FILE CONTENT:
{file_context}
"""

    response = llm.invoke([
        SystemMessage(content=DEBUG_PROMPT),
        HumanMessage(content=user),
    ])

    raw = _text(response)

    print("\n========== RAW GEMINI PATCH ==========")
    print(raw)
    print("========== END RAW GEMINI PATCH ==========\n")

    return raw
