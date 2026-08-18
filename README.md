# AutoFix Agent — Phase 1

A provider-agnostic local coding agent. Give it a GitHub repository URL and a GitHub issue URL/number (or issue title/description), and it will:

1. Clone the repository into an isolated local workspace.
2. Inspect the repository structure.
3. Ask a configurable LLM to identify relevant files and propose a fix.
4. Ask the LLM for a patch.
5. Apply the patch safely.
6. Run the repository's detected test command.
7. If tests fail, feed the failure back to the model and retry up to a bounded limit.
8. Show the final diff and test result.

## Supported LLM providers

- Ollama (default; local/free)
- OpenAI
- Anthropic
- Google Gemini

The agent layer never imports provider SDKs directly. Provider selection happens in `app/llm/factory.py`.

## Requirements

- Python 3.11+
- Git
- For Ollama: Ollama installed and running
- For cloud providers: the relevant API key

## Setup

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env
```

For local Ollama:

```bash
ollama pull qwen3:8b
ollama serve
```

Then:

```bash
python -m app.main
```

The CLI will ask for:

- GitHub repository URL
- GitHub issue URL
- Maximum repair iterations

If a public GitHub issue URL is supplied, the agent fetches the issue title and
description through the GitHub REST API. You can override them with CLI flags.

You can also run non-interactively:

```bash
python -m app.main ^
  --repo https://github.com/OWNER/REPO.git ^
  --issue-title "Fix parser crash" ^
  --issue-description "Parser crashes when input is empty."
```

## Provider configuration

### Ollama

```env
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:8b
OLLAMA_BASE_URL=http://localhost:11434
```

### OpenAI

```env
LLM_PROVIDER=openai
LLM_MODEL=<your-model>
OPENAI_API_KEY=...
```

### Anthropic

```env
LLM_PROVIDER=anthropic
LLM_MODEL=<your-model>
ANTHROPIC_API_KEY=...
```

### Gemini

```env
LLM_PROVIDER=gemini
LLM_MODEL=<your-model>
GOOGLE_API_KEY=...
```

Install the corresponding provider package if you use a cloud provider.

## Important Phase 1 limitations

This is deliberately a local Phase 1 implementation.

- Do not run it against repositories you do not trust.
- Repository tests are currently executed as local subprocesses.
- There is no Docker sandbox yet.
- There is no GitHub PR creation yet.
- The agent creates a local branch but does not push it.
- It does not automatically discover/select issues yet; you provide the issue URL.
- It supports Python test detection first; common JS test commands are also detected.
- The LLM is given bounded repository context, not the entire repository.

These are intentional follow-up phases.

## Architecture

```text
CLI
 |
 v
Workflow (LangGraph)
 |
 +--> Clone Repository
 |
 +--> Inspect Repository
 |
 +--> LLM Analysis
 |
 +--> Generate Patch
 |
 +--> Validate / Apply Patch
 |
 +--> Run Tests
 |
 +--> Debug / Retry
 |
 +--> Final Diff + Result
 |
 v
LLM Factory
 |------ Ollama
 |------ OpenAI
 |------ Anthropic
 `------ Gemini
```


## Phase 1 patch architecture

The model does not generate a Git diff. It returns structured exact text edits:
`file`, `old`, `new`, and `reason`.

The deterministic edit tool verifies that each `old` string exists exactly once,
applies the replacement, and lets Git generate the authoritative diff. This
avoids malformed LLM-generated hunks and cleanly separates probabilistic
reasoning from deterministic repository mutation.


## v3 edit matching

The deterministic edit layer first attempts an exact match. If that fails, it
normalizes CRLF/LF line endings and trailing whitespace and searches by line
window. It still refuses zero matches and ambiguous matches.

The workflow also refreshes repository context after every edit and before
every debugging iteration.


## v4 fixes

- Restores the repository-context refresh helper used after edits.
- Refreshes actual file contents before debugging.
- Phase 1 refuses test-file edits so the agent cannot make a failing test pass
  by weakening or changing the test.


## v5 test discovery

Python test discovery now recognizes common root-level files such as
`test_calculator.py` and `calculator_test.py`, in addition to tests inside a
`tests/` directory. This is important because small repositories frequently
keep source and test files at the repository root.


## v6 failure classification

Phase 1 now distinguishes:

- `PASSED` — finish successfully.
- `CODE_FAILURE` — send the failure to the debugging agent.
- `ENVIRONMENT_ERROR` — stop without spending an LLM call on source-code
  debugging.
- `TIMEOUT` — stop as an operational failure.
- `UNKNOWN_FAILURE` — treated conservatively as a non-success.

LLM provider errors are also normalized so quota/rate-limit failures do not
trigger an uncontrolled retry loop.


## v7 changes

- `MAX_RETRIES` replaces `MAX_ITERATIONS`.
- State tracks `retry_count`.
- One LangGraph-driven `tqdm` progress bar displays the current node and retry.
- Generated artifacts such as `__pycache__`, `*.pyc`, `.pytest_cache`,
  virtual environments, and `node_modules` are excluded from the final diff.
