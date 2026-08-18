# AutoFix --- Autonomous GitHub Issue Resolution Agent

> **Handoff / Continuation Document for Codex**
>
> This document is the source of truth for the current AutoFix idea,
> architecture, implementation status, engineering principles, known
> issues, and roadmap. Read this entire file before modifying the
> project. Continue from the existing implementation instead of
> redesigning the project from scratch.

------------------------------------------------------------------------

## 1. Project Overview

**AutoFix** is an autonomous software-engineering agent whose goal is:

> Given a GitHub repository and a GitHub issue, autonomously understand
> the issue, locate the relevant code, make the required code changes,
> run the repository's tests, analyze failures, iterate on the fix when
> necessary, and eventually produce a validated solution that can be
> committed and submitted as a Pull Request.

AutoFix is **not intended to be a coding chatbot**.

It is intended to become an autonomous SWE agent with an execution loop:

``` text
GitHub Issue
     ↓
Understand Issue
     ↓
Inspect Repository
     ↓
Locate Relevant Code
     ↓
Plan Fix
     ↓
Generate Structured Edits
     ↓
Apply Changes
     ↓
Run Tests
     ↓
 ┌───────────────────┐
 │ Tests pass?       │
 └─────────┬─────────┘
       No  │  Yes
           │
           ↓
     Analyze Failure
           ↓
       Debug/Fix
           ↓
       Run Tests
           │
           └──────────────→ Final Validated Fix
```

The core philosophy is:

> **Reliability before sophistication.**

Do not add advanced RAG, AST analysis, multi-agent orchestration, or
complex planning until the basic issue → edit → test → debug loop is
reliable.

------------------------------------------------------------------------

# 2. Repositories

## Main AutoFix Repository

GitHub:

`https://github.com/ShivNakil/autofix`

This is the actual AutoFix implementation.

## Test Repository

GitHub:

`https://github.com/ShivNakil/autofix-test-repo`

This repository is used to create controlled issues and verify that
AutoFix can autonomously solve them.

------------------------------------------------------------------------

# 3. Current Technology Stack

Primary language:

-   Python

Main orchestration:

-   LangGraph

LLM ecosystem:

-   LangChain
-   Provider-agnostic LLM abstraction
-   Gemini currently used for testing/prototyping

Testing:

-   pytest

Repository operations:

-   Git
-   GitHub API / GitHub integration

Other utilities:

-   Pydantic
-   tqdm

The architecture must remain **LLM-provider agnostic**.

AutoFix should not become tightly coupled to Gemini.

The conceptual architecture should support:

``` text
                    ┌── Gemini
                    │
AutoFix LLM Layer ──┼── OpenAI
                    │
                    ├── Claude
                    │
                    └── Other Providers
```

The workflow/orchestration code should not need to change when the LLM
provider changes.

------------------------------------------------------------------------

# 4. Product Goal

The long-term AutoFix experience should be:

``` text
Developer creates GitHub issue
              ↓
           AutoFix
              ↓
       Reads the issue
              ↓
      Understands repository
              ↓
      Finds relevant code
              ↓
        Plans a solution
              ↓
       Modifies source code
              ↓
         Runs tests
              ↓
      Debugs failures
              ↓
       Tests successfully
              ↓
       Creates git commit
              ↓
        Pushes branch
              ↓
      Creates GitHub PR
              ↓
       Developer reviews PR
```

Eventually the developer should not need to manually drive the coding
process.

The human should primarily provide:

``` text
Repository + Issue
```

and review the generated Pull Request.

------------------------------------------------------------------------

# 5. Current Phase

The project is currently focused on **Phase 1: Reliable Local Autonomous
Fixer**.

The immediate objective is NOT full GitHub PR automation.

The immediate objective is:

> Given a repository and issue, AutoFix must autonomously modify the
> local repository and produce a correct, test-validated fix.

Only after this becomes reliable should the project move to GitHub
branch/commit/PR automation.

------------------------------------------------------------------------

# 6. Current Phase 1 Architecture

The intended LangGraph workflow is approximately:

``` text
START
  ↓
fetch_issue
  ↓
clone_repository
  ↓
inspect_repository
  ↓
analyze_issue
  ↓
generate_edits
  ↓
apply_edits
  ↓
run_tests
  ↓
classify_result
  ↓
 ┌──────────────────────┐
 │                      │
 PASS                 FAIL
 │                      │
 ↓                      ↓
FINISH             analyze_failure
                        ↓
                    generate_fix
                        ↓
                    apply_fix
                        ↓
                    run_tests
                        │
                        └────────────→ classify_result
```

The exact node names may differ in the current source code. **Do not
rename everything simply to match this README if the current
implementation already has sensible names.**

The important thing is the behavior and separation of responsibilities.

------------------------------------------------------------------------

# 7. LangGraph State

AutoFix is an agentic state machine, not a simple prompt/response
program.

The state should contain the information needed to continue the workflow
safely.

Conceptually:

``` python
state = {
    "issue": ...,
    "repository": ...,
    "repo_path": ...,
    "branch": ...,
    "repository_context": ...,
    "relevant_files": ...,
    "issue_analysis": ...,
    "proposed_edits": ...,
    "applied_edits": ...,
    "test_results": ...,
    "failure_analysis": ...,
    "iteration": ...,
    "final_diff": ...,
}
```

Do not blindly add every possible field.

State should remain explicit, typed, and understandable.

Prefer Pydantic models / TypedDict / structured state where appropriate.

------------------------------------------------------------------------

# 8. Important Design Decision: Structured Edits

One of the most important architectural decisions is:

> **Do not rely on the LLM to generate arbitrary raw git patches as the
> primary editing mechanism.**

Raw patch generation is fragile.

The model should instead generate structured edits.

Conceptual example:

``` text
File:
calculator.py

Find:
    return a * b

Replace:
    return a - b
```

Or an equivalent structured representation such as:

``` json
{
  "file": "calculator.py",
  "old_text": "return a * b",
  "new_text": "return a - b"
}
```

The deterministic editing layer should:

1.  Validate the target file.
2.  Validate the old content.
3.  Ensure the replacement is unambiguous.
4.  Apply the change.
5.  Report exactly what changed.
6.  Fail safely if the expected source cannot be found.

The LLM should decide **what** needs to change.

The deterministic editing system should control **how** the change is
applied.

------------------------------------------------------------------------

# 9. Issue Ingestion

AutoFix receives a GitHub issue.

Conceptually:

``` text
Repository:
ShivNakil/autofix-test-repo

Issue:
#3

Title:
Calculator subtraction is broken

Description:
The calculator should subtract two numbers,
but the implementation currently performs the wrong operation.
```

The agent should obtain the actual issue content rather than relying on
a manually copied prompt in the final architecture.

The issue should be converted into structured context containing, where
available:

-   Issue number
-   Title
-   Description/body
-   Labels
-   Repository information
-   Author
-   Relevant metadata

Do not unnecessarily send irrelevant GitHub metadata to the LLM.

------------------------------------------------------------------------

# 10. Repository Acquisition

The agent needs an isolated working copy.

Conceptually:

``` text
Repository
    ↓
Clone
    ↓
Working directory
    ↓
Working branch
    ↓
AutoFix operations
```

The repository must not be modified destructively outside the intended
workspace.

The long-term implementation should support isolated
execution/sandboxing.

------------------------------------------------------------------------

# 11. Repository Inspection

The agent should first understand the repository before editing.

At minimum it should be able to determine:

``` text
What files exist?
What language(s) are used?
What is the project structure?
Where are the tests?
What files are likely relevant to the issue?
How is the project executed?
```

Do NOT dump an entire large repository into the LLM.

The repository inspection layer should progressively become more
intelligent.

Initial approach can be simple.

Later approaches may include:

-   File tree analysis
-   Relevant-file heuristics
-   AST analysis
-   Symbol resolution
-   Dependency analysis
-   Repository indexing
-   Embeddings/RAG

But these are later phases.

------------------------------------------------------------------------

# 12. Issue Analysis

The LLM receives:

``` text
Issue
+
Relevant repository context
```

and determines:

``` text
What is wrong?
What behavior is expected?
Which files are relevant?
Which functions/classes are relevant?
What change is likely required?
What tests should validate the change?
```

The result should preferably be structured rather than an unbounded
prose response.

For example:

``` text
IssueAnalysis
├── problem
├── expected_behavior
├── relevant_files
├── relevant_symbols
├── proposed_solution
└── validation_strategy
```

The agent should avoid making speculative changes outside the issue
scope.

------------------------------------------------------------------------

# 13. Code Modification

The modification stage receives the issue analysis and generates
structured edits.

Example:

``` text
Issue:
Fix subtraction behavior.

Analysis:
calculator.py contains the affected method.

Edit:
calculator.py
    replace:
        return a * b
    with:
        return a - b
```

The edit application layer then performs the deterministic change.

After modification, AutoFix should be able to produce a diff.

------------------------------------------------------------------------

# 14. Test Execution

After applying changes, AutoFix must validate the result.

For Python projects, the initial implementation uses:

``` bash
pytest
```

The test execution layer must capture:

-   Exit code
-   stdout
-   stderr
-   Test failures
-   Passed test count where available
-   Execution duration where useful

Example:

``` text
Exit code: 0

3 tests passed
```

means success.

A non-zero exit code should generally be treated as failure, but the
result should be represented explicitly so the agent can reason about
it.

------------------------------------------------------------------------

# 15. Debug / Retry Loop

The most important autonomous behavior is the test/debug loop.

If tests fail:

``` text
Test Failure
     ↓
Read failure output
     ↓
Analyze failure
     ↓
Determine root cause
     ↓
Generate correction
     ↓
Apply correction
     ↓
Run tests again
```

This must be **bounded**.

The agent must never enter an infinite repair loop.

------------------------------------------------------------------------

# 16. MAX_RETRIES Semantics

This is an important implementation rule.

`MAX_RETRIES` should represent:

> Maximum number of test-failure → analysis → fix → test cycles.

It should NOT mean:

> Maximum number of times LangGraph may execute arbitrary nodes.

Do not introduce a generic global iteration limit and call it
`MAX_RETRIES`.

Example:

``` text
Initial implementation
      ↓
Run tests
      ↓
FAIL
      ↓
Retry #1
      ↓
Run tests
      ↓
FAIL
      ↓
Retry #2
      ↓
Run tests
      ↓
PASS
```

If the retry limit is reached:

``` text
FAILED:
Maximum debugging attempts reached.
```

The agent should return a useful diagnostic rather than looping
indefinitely.

------------------------------------------------------------------------

# 17. Known Regression / Implementation Lessons

Recent implementation work exposed a few regressions.

### Regression: `args.max_iterations`

A version introduced/renamed an argument involving:

``` text
args.max_iterations
```

incorrectly.

Do not blindly introduce this field again.

Use a clear and consistent retry configuration.

### Regression: undefined `repo_url`

A version referenced:

``` text
repo_url
```

where the variable was not defined in the relevant scope.

The lesson is:

> Keep state and function inputs explicit. Do not rely on
> implicit/global variables.

When refactoring, run the actual application/test suite instead of
assuming a node still has variables from an older implementation.

------------------------------------------------------------------------

# 18. Current Proof of Concept

The current implementation has already demonstrated the basic happy
path.

On the test repository, AutoFix handled an issue where a calculator
operation was incorrect.

The affected code was conceptually:

``` python
return a * b
```

and the required fix was:

``` python
return a - b
```

After applying the change:

``` text
3 tests passed
```

This proves the fundamental loop:

``` text
Issue
 ↓
Understand
 ↓
Locate code
 ↓
Modify code
 ↓
Run tests
 ↓
Successful validation
```

This is an important milestone.

Do not discard this working behavior while adding future architecture.

------------------------------------------------------------------------

# 19. CLI / Progress Display

A useful AutoFix CLI should expose workflow progress.

Preferred direction:

``` text
AutoFix  ━━━━━━━━━━━━━━━━━━━━━━━  6/8

✓ Fetch issue
✓ Clone repository
✓ Inspect repository
✓ Analyze issue
✓ Apply edits
● Running tests
○ Debug
○ Finalize
```

The progress indicator should be based on **actual LangGraph node/stream
execution**.

Do not create a fake percentage that increments regardless of actual
work.

The preferred direction is one tqdm progress bar driven from the
LangGraph streaming/events.

The UI should remain secondary to correctness.

------------------------------------------------------------------------

# 20. Provider Abstraction

The LLM layer should be abstracted.

Conceptually:

``` text
                 ┌─────────────┐
                 │  LLM Layer  │
                 └──────┬──────┘
                        │
        ┌───────────────┼───────────────┐
        ↓               ↓               ↓
     Gemini          OpenAI          Claude
```

The rest of AutoFix should interact with a stable abstraction.

For example:

``` text
analyze_issue(...)
generate_edits(...)
analyze_test_failure(...)
```

The exact class/function names should follow the existing project
conventions.

Do not over-engineer this abstraction prematurely.

------------------------------------------------------------------------

# 21. What AutoFix Should NOT Do Yet

Do not prematurely implement all of the following in Phase 1:

-   Full multi-agent architecture
-   Complex autonomous planning
-   Large-scale repository RAG
-   Sophisticated vector database infrastructure
-   AST intelligence for every language
-   Automatic PR merging
-   Automatic production deployment
-   Unlimited autonomous retries
-   Broad repository-wide refactoring
-   Unbounded shell command execution
-   Destructive operations on the user's machine

The priority is:

``` text
Correctness
>
Reliability
>
Observability
>
Architecture
>
Advanced intelligence
```

------------------------------------------------------------------------

# 22. Phase Roadmap

## Phase 1 --- Reliable Local Autonomous Fixer

### Goal

Given:

``` text
Repository + Issue
```

produce:

``` text
Validated local code fix
```

### Status

**Mostly implemented / active hardening phase.**

### Completed

-   [x] Python project established
-   [x] LangGraph workflow
-   [x] Git repository handling
-   [x] GitHub issue concept/integration
-   [x] Repository inspection
-   [x] LLM issue analysis
-   [x] Structured code-edit concept
-   [x] Code modification
-   [x] pytest execution
-   [x] Basic successful fix
-   [x] Basic agent loop
-   [x] Gemini-based prototype

### Still to harden

-   [ ] Clean state management
-   [ ] Provider abstraction
-   [ ] Robust structured edit validation
-   [ ] Better error handling
-   [ ] Reliable retry/debug loop
-   [ ] Accurate test result parsing
-   [ ] Streaming progress UI
-   [ ] Regression tests for every node
-   [ ] End-to-end integration tests
-   [ ] Clean failure reporting
-   [ ] Repository cleanup after execution

------------------------------------------------------------------------

# 23. Phase 2 --- GitHub PR Automation

Once Phase 1 is reliable:

``` text
GitHub Issue
      ↓
AutoFix
      ↓
Clone
      ↓
Create branch
      ↓
Analyze
      ↓
Fix
      ↓
Test
      ↓
Commit
      ↓
Push
      ↓
Create Pull Request
```

Expected capabilities:

-   [ ] Create isolated branch
-   [ ] Commit changes
-   [ ] Push branch
-   [ ] Generate commit message
-   [ ] Generate PR title
-   [ ] Generate PR description
-   [ ] Link PR to issue
-   [ ] Include test results
-   [ ] Include summary of changed files
-   [ ] Include known limitations
-   [ ] Return PR URL

The PR should be **reviewable**, not silently merged.

------------------------------------------------------------------------

# 24. Phase 3 --- Sandboxed Execution

AutoFix will eventually execute code from arbitrary repositories.

This introduces security risks.

The execution environment should therefore be isolated.

Target architecture:

``` text
AutoFix
   ↓
Sandbox / Container
   ↓
Clone Repository
   ↓
Modify
   ↓
Build/Test
   ↓
Results
```

Sandbox controls should eventually cover:

-   Filesystem
-   Network
-   CPU
-   Memory
-   Process count
-   Execution time
-   Credentials/secrets
-   Shell access

Never assume a repository's code or build scripts are trusted.

------------------------------------------------------------------------

# 25. Phase 4 --- Repository Intelligence

For larger repositories, simple file inspection will not be sufficient.

Add progressively:

### AST analysis

Understand:

``` text
classes
functions
methods
imports
calls
variables
```

### Symbol resolution

Example:

``` text
calculate()
    ↓
Calculator.calculate()
    ↓
calculator.py
```

### Dependency analysis

Example:

``` text
api.py
  ↓
service.py
  ↓
calculator.py
  ↓
database.py
```

### Repository indexing / RAG

Eventually:

``` text
Repository
     ↓
Parse
     ↓
Chunk
     ↓
Index
     ↓
Retrieve relevant code
     ↓
LLM
```

This prevents huge irrelevant repositories from being sent to the model.

------------------------------------------------------------------------

# 26. Phase 5 --- Advanced Planning

Once repository intelligence is reliable, improve the planner.

The planner should be able to create a bounded plan such as:

``` text
1. Inspect failing test.
2. Find implementation.
3. Identify incorrect behavior.
4. Inspect related tests.
5. Modify implementation.
6. Run targeted tests.
7. Run full test suite.
```

The plan should remain bounded and observable.

Avoid allowing an LLM to create an unlimited recursive task tree.

------------------------------------------------------------------------

# 27. Phase 6 --- Multi-Agent SWE Architecture

Long-term architecture can become:

``` text
                    ┌──────────────┐
                    │   Planner    │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │   Explorer   │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │    Coder     │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │    Tester    │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │   Debugger   │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │   Reviewer   │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │ PR Generator │
                    └──────────────┘
```

Possible responsibilities:

### Planner

Understand issue and create bounded implementation plan.

### Explorer

Find relevant files, symbols, tests, and dependencies.

### Coder

Generate structured code edits.

### Tester

Run appropriate tests.

### Debugger

Analyze test/build failures and propose corrections.

### Reviewer

Check whether the implementation actually satisfies the issue and
whether the change is unnecessarily broad.

### PR Generator

Prepare commit and Pull Request metadata.

Again:

**Do not implement this before Phase 1 is stable.**

------------------------------------------------------------------------

# 28. Long-Term Architecture

The eventual system should look roughly like:

``` text
                       GitHub
                         │
                    GitHub Issue
                         │
                         ▼
                ┌─────────────────┐
                │    AutoFix      │
                │   Controller     │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │   LangGraph     │
                │   Orchestrator  │
                └────────┬────────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
     Repository      LLM Layer      Execution
     Intelligence                   Sandbox
          │              │              │
          │       ┌──────┼──────┐       │
          │       │      │      │       │
          │     Gemini OpenAI Claude     │
          │                             │
          └──────────────┬──────────────┘
                         ▼
                  Validated Fix
                         │
                         ▼
                    Git Branch
                         │
                         ▼
                   Pull Request
```

------------------------------------------------------------------------

# 29. Engineering Principles

## 29.1 Deterministic operations should stay deterministic

Use the LLM for:

-   Understanding
-   Planning
-   Reasoning
-   Code-change proposal
-   Failure analysis

Use deterministic code for:

-   File operations
-   Git operations
-   Applying validated edits
-   Running tests
-   Parsing structured results
-   Retry counting
-   Safety checks

------------------------------------------------------------------------

## 29.2 Never trust LLM output blindly

Validate:

-   File paths
-   Edit targets
-   Old text
-   New text
-   Structured output schema
-   Command requests
-   Test results

------------------------------------------------------------------------

## 29.3 Keep the agent bounded

Every autonomous loop needs limits.

Examples:

``` text
MAX_RETRIES
MAX_FILES_CHANGED
MAX_EXECUTION_TIME
MAX_OUTPUT_SIZE
```

Only introduce limits that have clear semantics.

------------------------------------------------------------------------

## 29.4 Preserve the working path

Do not perform a large refactor simply because a cleaner architecture
seems possible.

When modifying the project:

1.  Understand the existing implementation.
2.  Identify the smallest required change.
3.  Preserve working behavior.
4.  Run tests.
5.  Add regression tests.
6.  Then refactor if necessary.

------------------------------------------------------------------------

## 29.5 Observability matters

Every major agent action should eventually be observable:

``` text
What did the agent do?
Why did it do it?
What files did it inspect?
What files did it modify?
What tests did it run?
Why did a test fail?
How many retries occurred?
What is the final diff?
```

This is essential for debugging an autonomous system.

------------------------------------------------------------------------

# 30. Testing Strategy

AutoFix itself needs tests.

Do not rely only on the test repository.

Recommended test layers:

## Unit tests

Test:

-   State models
-   Git helpers
-   Issue parsing
-   Structured edit validation
-   Edit application
-   Test-result parsing
-   Retry counting

## Integration tests

Test:

``` text
Issue
 ↓
Repository
 ↓
Agent
 ↓
Edit
 ↓
Test
```

## End-to-end tests

Use `autofix-test-repo` with intentionally created issues.

Example:

``` text
Issue A → simple Python bug
Issue B → bug requiring multiple files
Issue C → test failure requiring debugging
Issue D → malformed/ambiguous issue
Issue E → no valid fix
```

The goal is not only to prove success.

The agent must fail safely when it cannot confidently solve an issue.

------------------------------------------------------------------------

# 31. Success Criteria for Phase 1

Phase 1 should be considered complete only when AutoFix can reliably
handle a meaningful set of controlled issues.

A successful run should produce:

``` text
✓ Issue fetched
✓ Repository cloned
✓ Relevant code identified
✓ Solution generated
✓ Structured edits validated
✓ Changes applied
✓ Tests executed
✓ Tests passed
✓ Final diff generated
✓ Workspace cleaned
```

For a failed run:

``` text
✓ Issue fetched
✓ Repository cloned
✓ Analysis attempted
✓ Changes bounded
✓ Tests executed
✓ Failure diagnosed
✓ Retry limit respected
✓ Clear failure reason returned
✓ No infinite loop
✓ Workspace cleaned
```

------------------------------------------------------------------------

# 32. Recommended Immediate Work

The next implementation work should focus on **hardening Phase 1**, in
approximately this order:

### Step 1 --- Inspect the existing repository

Before writing code:

``` text
Read:
- project structure
- README
- pyproject/requirements
- entrypoint
- graph definition
- state definitions
- nodes
- tools
- LLM/provider code
- test suite
```

Do not assume this README exactly matches the current source tree.

The source code is authoritative for current implementation details.

------------------------------------------------------------------------

### Step 2 --- Run the current project

First reproduce the current behavior.

Run the existing commands documented by the project.

Confirm:

-   Current startup command
-   Current errors/warnings
-   Current successful workflow
-   Current test results

Do not start refactoring before establishing a baseline.

------------------------------------------------------------------------

### Step 3 --- Fix regressions

Pay particular attention to the previously observed problems:

``` text
args.max_iterations
```

and:

``` text
undefined repo_url
```

Make the state/configuration flow explicit.

------------------------------------------------------------------------

### Step 4 --- Stabilize structured edits

Make sure the edit system handles:

``` text
valid edit
missing file
missing old text
multiple matches
multiple files
invalid path
partial failure
```

safely.

------------------------------------------------------------------------

### Step 5 --- Stabilize test/debug loop

Implement:

``` text
apply
 ↓
test
 ↓
failure?
 ↓
analyze
 ↓
retry
```

with explicit bounded retry semantics.

------------------------------------------------------------------------

### Step 6 --- Add regression tests

Every bug discovered during development should become a regression test.

Do not repeatedly fix the same class of problem manually.

------------------------------------------------------------------------

### Step 7 --- Improve progress reporting

Once workflow behavior is stable, connect tqdm/progress output to actual
LangGraph execution.

------------------------------------------------------------------------

### Step 8 --- Provider abstraction

Separate Gemini-specific code from generic AutoFix reasoning interfaces.

Do not over-engineer it.

------------------------------------------------------------------------

# 33. Definition of Done for the Immediate Milestone

The immediate milestone is:

> **AutoFix can solve controlled GitHub issues in a local repository
> reliably without manual intervention.**

Example:

``` text
Input:
Repository = autofix-test-repo
Issue = #3

AutoFix:
1. Fetches issue.
2. Clones repository.
3. Inspects files.
4. Identifies calculator.py.
5. Understands incorrect operation.
6. Generates structured edit.
7. Applies edit.
8. Runs pytest.
9. Gets 3 passing tests.
10. Produces final diff.
11. Finishes successfully.
```

The same workflow should work for more than one trivial issue before
declaring Phase 1 complete.

------------------------------------------------------------------------

# 34. Important Instruction for Codex

When continuing this project:

### DO

-   Read the existing source code first.
-   Preserve working behavior.
-   Run tests before and after changes.
-   Make small, verifiable changes.
-   Keep LangGraph as the orchestration layer.
-   Keep LLM provider abstraction in mind.
-   Keep structured edits.
-   Keep retry behavior bounded.
-   Add regression tests.
-   Prefer explicit state over hidden globals.
-   Keep deterministic operations outside the LLM.
-   Report failures clearly.

### DO NOT

-   Rewrite the entire project from scratch.
-   Replace LangGraph without a strong reason.
-   Replace structured edits with raw patches.
-   Couple the entire project to one LLM provider.
-   Add multi-agent complexity prematurely.
-   Add RAG prematurely.
-   Introduce unbounded loops.
-   Give the LLM unrestricted shell access.
-   Assume tests passing once means the architecture is complete.
-   Change public interfaces casually.
-   Remove working functionality merely to simplify the implementation.

------------------------------------------------------------------------

# 35. Decision Hierarchy

When making implementation decisions, use this priority:

``` text
1. Existing working behavior
2. Correctness
3. Safety
4. Testability
5. Observability
6. Simplicity
7. Extensibility
8. Performance optimization
9. Advanced agent intelligence
```

If an advanced architecture makes the basic workflow less reliable,
choose the simpler architecture.

------------------------------------------------------------------------

# 36. Final Vision

AutoFix should eventually become a real autonomous software-engineering
system:

``` text
Developer
    │
    │ creates GitHub Issue
    ▼
┌─────────────────────┐
│       AutoFix       │
└──────────┬──────────┘
           │
           ▼
     Understand Issue
           │
           ▼
   Understand Repository
           │
           ▼
      Plan Solution
           │
           ▼
      Modify Code
           │
           ▼
       Run Tests
           │
       ┌───┴───┐
       │       │
     PASS    FAIL
       │       │
       │       ▼
       │    Debug
       │       │
       │       └──────→ Run Tests
       │
       ▼
   Review Changes
       │
       ▼
   Commit Changes
       │
       ▼
    Push Branch
       │
       ▼
   Create GitHub PR
       │
       ▼
   Human Review
```

The end goal is not simply:

> "AI writes code."

The end goal is:

> **AI performs a bounded, observable, test-validated
> software-engineering task from issue to Pull Request.**

------------------------------------------------------------------------

# 37. Current Project Status Summary

``` text
                         AutoFix
                            │
             ┌──────────────┴──────────────┐
             │                             │
          COMPLETED                     NEXT
             │                             │
             ▼                             ▼
      LangGraph workflow          Harden Phase 1
      GitHub issue handling       Structured edits
      Repo acquisition            Test/debug loop
      Repo inspection             Provider abstraction
      LLM reasoning               Regression tests
      Code modification           Progress streaming
      pytest execution
      Basic retry concept
      Basic successful fix
             │
             ▼
       PROVEN POC
             │
             ▼
      Phase 2: GitHub PR
             │
             ▼
      Phase 3: Sandbox
             │
             ▼
   Phase 4: Repo Intelligence
             │
             ▼
     Phase 5: Planning
             │
             ▼
   Phase 6: Multi-Agent SWE
```

------------------------------------------------------------------------

# 38. One-Sentence Project Definition

**AutoFix is a LangGraph-based, provider-agnostic autonomous
software-engineering agent that takes a GitHub issue, understands the
repository, generates and applies structured code changes, validates
them through tests, iteratively debugs failures within bounded limits,
and ultimately aims to create a reviewable GitHub Pull Request.**

------------------------------------------------------------------------

## END OF AUTOFIX HANDOFF DOCUMENT

**Codex: Start by inspecting the current repository and establishing a
baseline. Do not assume that the source code exactly matches this
document. Use this README as the architectural/product context, and use
the existing source code and tests as the authority for the current
implementation.**
