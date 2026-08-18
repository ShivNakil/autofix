from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.prompts import ANALYSIS_PROMPT, EDIT_PROMPT, DEBUG_PROMPT
from app.llm.factory import get_llm
from app.models.edits import CodeEditPlan

def _text(response) -> str:
    content = response.content
    return content if isinstance(content, str) else str(content)

def analyze(issue_title, issue_description, repository_structure, search_results, file_context):
    response = get_llm().invoke([
        SystemMessage(content=ANALYSIS_PROMPT),
        HumanMessage(content=f"""ISSUE TITLE:
{issue_title}

ISSUE DESCRIPTION:
{issue_description}

REPOSITORY STRUCTURE:
{repository_structure}

SEARCH RESULTS:
{search_results}

RELEVANT FILE CONTENT:
{file_context}
"""),
    ])
    return _text(response)

def generate_edits(issue_title, issue_description, analysis, file_context) -> CodeEditPlan:
    response = get_llm().with_structured_output(CodeEditPlan).invoke([
        SystemMessage(content=EDIT_PROMPT),
        HumanMessage(content=f"""ISSUE TITLE:
{issue_title}

ISSUE DESCRIPTION:
{issue_description}

ENGINEERING ANALYSIS:
{analysis}

CURRENT RELEVANT FILE CONTENT:
{file_context}
"""),
    ])
    return response if isinstance(response, CodeEditPlan) else CodeEditPlan.model_validate(response)

def debug_edits(issue_title, issue_description, analysis, test_output, file_context) -> CodeEditPlan:
    response = get_llm().with_structured_output(CodeEditPlan).invoke([
        SystemMessage(content=DEBUG_PROMPT),
        HumanMessage(content=f"""ISSUE TITLE:
{issue_title}

ISSUE DESCRIPTION:
{issue_description}

PREVIOUS ANALYSIS:
{analysis}

TEST FAILURE:
{test_output}

CURRENT RELEVANT FILE CONTENT:
{file_context}
"""),
    ])
    return response if isinstance(response, CodeEditPlan) else CodeEditPlan.model_validate(response)
