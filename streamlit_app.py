#!/usr/bin/env python3
"""
Streamlit UI for AutoFix Agent Phase 1
Provides a user-friendly web interface for the AutoFix Agent
"""

import streamlit as st
import subprocess
import sys
import os
from pathlib import Path

# Add the app directory to Python path so we can import from it
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.config import settings
from app.workflow.graph import build_graph
from app.models.state import AgentState

def main():
    st.set_page_config(
        page_title="AutoFix Agent",
        page_icon="🔧",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("🔧 AutoFix Agent")
    st.markdown("*A provider-agnostic local coding agent that fixes GitHub issues*")

    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")

        # LLM Provider Selection
        llm_provider = st.selectbox(
            "LLM Provider",
            options=["ollama", "openai", "anthropic", "gemini"],
            index=0,
            help="Select the LLM provider to use"
        )

        # Model selection based on provider
        if llm_provider == "ollama":
            llm_model = st.text_input(
                "Model Name",
                value="qwen3:8b",
                help="Ollama model name (e.g., qwen3:8b, llama2, codellama)"
            )
            ollama_url = st.text_input(
                "Ollama Base URL",
                value="http://localhost:11434",
                help="URL where Ollama is running"
            )
        elif llm_provider == "openai":
            llm_model = st.text_input(
                "Model Name",
                value="gpt-3.5-turbo",
                help="OpenAI model name (e.g., gpt-3.5-turbo, gpt-4)"
            )
            openai_key = st.text_input(
                "OpenAI API Key",
                type="password",
                help="Your OpenAI API key"
            )
        elif llm_provider == "anthropic":
            llm_model = st.text_input(
                "Model Name",
                value="claude-3-haiku-20240307",
                help="Anthropic model name (e.g., claude-3-haiku-20240307, claude-3-sonnet-20240229)"
            )
            anthropic_key = st.text_input(
                "Anthropic API Key",
                type="password",
                help="Your Anthropic API key"
            )
        elif llm_provider == "gemini":
            llm_model = st.text_input(
                "Model Name",
                value="gemini-pro",
                help="Gemini model name (e.g., gemini-pro, gemini-1.5-pro)"
            )
            google_key = st.text_input(
                "Google API Key",
                type="password",
                help="Your Google API key for Gemini"
            )

        # Advanced settings
        with st.expander("Advanced Settings"):
            max_retries = st.slider(
                "Maximum Retries",
                min_value=1,
                max_value=10,
                value=3,
                help="Maximum number of retry attempts if tests fail"
            )
            test_timeout = st.slider(
                "Test Timeout (seconds)",
                min_value=30,
                max_value=300,
                value=120,
                help="Timeout for test execution"
            )
            workspace_dir = st.text_input(
                "Workspace Directory",
                value="workspace",
                help="Directory where repositories will be cloned"
            )

    # Main form
    st.header("📝 Issue Details")

    col1, col2 = st.columns([2, 1])

    with col1:
        repo_url = st.text_input(
            "GitHub Repository URL",
            placeholder="https://github.com/owner/repo.git",
            help="The GitHub repository to fix (must end with .git)"
        )

        issue_url = st.text_input(
            "GitHub Issue URL (Optional)",
            placeholder="https://github.com/owner/repo/issues/123",
            help="If provided, the agent will fetch the issue title and description automatically"
        )

    with col2:
        if st.button("🔍 Fetch Issue", help="Fetch issue details from GitHub"):
            if issue_url:
                with st.spinner("Fetching issue from GitHub..."):
                    try:
                        # Import here to avoid circular imports
                        from app.tools.github import fetch_public_issue
                        issue_data = fetch_public_issue(issue_url)
                        st.session_state.fetched_issue = issue_data
                        st.success(f"Fetched issue: {issue_data['title']}")
                    except Exception as e:
                        st.error(f"Could not fetch issue: {str(e)}")
            else:
                st.warning("Please provide a GitHub issue URL")

    # Issue title and description
    issue_title = st.text_input(
        "Issue Title",
        value=st.session_state.get('fetched_issue', {}).get('title', ''),
        placeholder="Enter issue title here",
        help="Title of the issue to fix"
    )

    issue_description = st.text_area(
        "Issue Description",
        value=st.session_state.get('fetched_issue', {}).get('description', ''),
        height=150,
        placeholder="Enter issue description here...",
        help="Detailed description of the issue to fix"
    )

    # Run button
    if st.button("🚀 Start AutoFix Agent", type="primary", use_container_width=True):
        if not repo_url:
            st.error("Please provide a GitHub repository URL")
            return

        if not issue_title:
            st.error("Please provide an issue title")
            return

        if not issue_description:
            st.error("Please provide an issue description")
            return

        # Validate repo URL
        if not repo_url.endswith('.git'):
            st.warning("Repository URL should end with .git for best results")

        # Run the agent
        run_autofix_agent(
            repo_url=repo_url,
            issue_title=issue_title,
            issue_description=issue_description,
            issue_url=issue_url,
            llm_provider=llm_provider,
            llm_model=llm_model,
            max_retries=max_retries,
            test_timeout=test_timeout,
            workspace_dir=workspace_dir,
            ollama_url=ollama_url if llm_provider == "ollama" else None,
            openai_key=openai_key if llm_provider == "openai" else None,
            anthropic_key=anthropic_key if llm_provider == "anthropic" else None,
            google_key=google_key if llm_provider == "gemini" else None
        )

def run_autofix_agent(
    repo_url,
    issue_title,
    issue_description,
    issue_url="",
    llm_provider="ollama",
    llm_model="qwen3:8b",
    max_retries=3,
    test_timeout=120,
    workspace_dir="workspace",
    ollama_url=None,
    openai_key=None,
    anthropic_key=None,
    google_key=None
):
    """Run the AutoFix Agent with the given parameters"""

    # Set environment variables for configuration
    os.environ["LLM_PROVIDER"] = llm_provider
    os.environ["LLM_MODEL"] = llm_model
    os.environ["MAX_RETRIES"] = str(max_retries)
    os.environ["TEST_TIMEOUT_SECONDS"] = str(test_timeout)
    os.environ["WORKSPACE_DIR"] = workspace_dir

    if llm_provider == "ollama" and ollama_url:
        os.environ["OLLAMA_BASE_URL"] = ollama_url
    elif llm_provider == "openai" and openai_key:
        os.environ["OPENAI_API_KEY"] = openai_key
    elif llm_provider == "anthropic" and anthropic_key:
        os.environ["ANTHROPIC_API_KEY"] = anthropic_key
    elif llm_provider == "gemini" and google_key:
        os.environ["GOOGLE_API_KEY"] = google_key

    # Create progress containers
    progress_container = st.container()
    results_container = st.container()

    with progress_container:
        st.info("🚀 Starting AutoFix Agent...")
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Prepare initial state
        initial_state = {
            "repo_url": repo_url,
            "issue_url": issue_url,
            "issue_title": issue_title,
            "issue_description": issue_description,
            "retry_count": 0,
            "max_retries": max_retries,
            "final_status": "STARTED",
        }

        try:
            # Build and run the graph
            graph = build_graph()

            # We'll simulate the progress since we can't easily intercept the graph streaming
            # In a real implementation, we'd hook into the graph's streaming mechanism
            status_text.text("Initializing workflow...")
            progress_bar.progress(10)

            # Run the graph (this will block until completion)
            with st.spinner("Running AutoFix Agent... This may take several minutes."):
                final_state = graph.invoke(initial_state)

            progress_bar.progress(100)
            status_text.text("AutoFix Agent completed!")

        except Exception as e:
            st.error(f"Error running AutoFix Agent: {str(e)}")
            return

    # Display results
    with results_container:
        st.header("📊 Results")

        # Status
        status = final_state.get("final_status", "UNKNOWN")
        status_colors = {
            "SUCCESS": "green",
            "FAILED": "red",
            "TIMEOUT": "orange",
            "ENVIRONMENT_ERROR": "orange",
            "NO_SAFE_EDIT": "blue"
        }
        status_color = status_colors.get(status, "gray")

        st.markdown(f"**Final Status:** :{status_color}[{status}]")

        # Analysis
        if final_state.get("analysis"):
            with st.expander("🔍 Analysis", expanded=True):
                st.markdown(final_state["analysis"])

        # Test Command
        if final_state.get("test_command"):
            st.markdown(f"**Test Command:** `{final_state['test_command']}`")

        # Test Output
        if final_state.get("test_output"):
            with st.expander("🧪 Test Output", expanded=False):
                st.text(final_state["test_output"][-2000:])  # Show last 2000 chars

        # Git Diff
        if final_state.get("final_diff"):
            with st.expander("📋 Git Diff", expanded=True):
                if final_state["final_diff"].strip():
                    st.code(final_state["final_diff"], language="diff")
                else:
                    st.info("No changes were made to the repository")

        # Repository Info
        col1, col2 = st.columns(2)
        with col1:
            if final_state.get("repository_path"):
                st.markdown(f"**Repository Path:** `{final_state['repository_path']}`")
        with col2:
            if final_state.get("branch_name"):
                st.markdown(f"**Branch:** `{final_state['branch_name']}`")

        # Retry count
        retry_count = final_state.get("retry_count", 0)
        if retry_count > 0:
            st.markdown(f"**Retries Attempted:** {retry_count}/{max_retries}")

if __name__ == "__main__":
    main()