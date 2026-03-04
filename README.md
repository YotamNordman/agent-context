# agent-context

Deterministic context injection for AI agent workspaces. Analyzes workspace structure and injects task-aware instruction files (`.github/instructions/*.md`) so agents get high-quality guidance without wasting context tokens on framework tutorials or style conventions they already know.

## Overview

agent-context is a lightweight system that bridges workspace analysis, tool profile management, and instruction generation. It ensures Copilot agents working on projects have access to:

- **Workspace-specific instructions** — detected languages, frameworks, test/build commands
- **Tool profiles** — MCP servers and custom agents available for that project  
- **Skill bundles** — collections of MCP servers, templates, agents, and environment variables
- **Completion guidance** — checklists that address top failure modes (incomplete work, placeholder content, missing tests)

## Problem Statement

Analysis of agent failures showed they consistently:
- ✗ Leave work incomplete (declare done at 30-60%)
- ✗ Leave placeholder content (`[INSERT X]`, `TODO`)
- ✗ Reference non-existent files in documentation
- ✗ Forget to run tests before committing

Traditional style guides don't help — agents already know Python/JS conventions. **agent-context solves this by injecting task-aware, workspace-specific guidance in ~670 tokens.**

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Workspace                                                   │
│ (Python/JS/Docker/K8s files, pyproject.toml, package.json) │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Analyzer                                                    │
│ - Detects languages, frameworks                            │
│ - Finds test runners, build/lint commands                  │
│ - Discovers source/test directories                        │
│ Output: WorkspaceInfo dataclass                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Renderer                                                    │
│ - Loads Jinja2 templates (4 template files)                │
│ - Renders workspace-aware instruction files                │
│ - Includes task context (task_id, feedback, criteria)      │
│ Output: Dict[filename → content]                           │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   [Templates]   [Profiles]   [SkillBundles]
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Injector                                                    │
│ - Writes instruction files to .github/instructions/        │
│   (except copilot-instructions.md → .github/)              │
│ - Generates mcp-config.json (if profile specified)         │
│ Output: {filename → "written"|"skipped"|"error"}           │
└─────────────────────────────────────────────────────────────┘
        │                          │
        ▼                          ▼
  [.instructions.md]         [mcp-config.json]
   files in workspace        (MCP server config)
```

## Core Concepts

### Workspace Analysis
The analyzer detects:
- **Languages**: Python, JavaScript/TypeScript, Go, Java, Rust
- **Frameworks**: Django, FastAPI, Flask, React, Vue, Next.js, etc.
- **Test runners**: pytest, jest, vitest, go test, cargo test, maven test
- **Build/lint commands**: from pyproject.toml, package.json, Cargo.toml, go.mod
- **Infrastructure**: Dockerfile, K8s manifests, GitHub Actions workflows
- **Source/test directories**: src/, tests/, test/, __tests__/, etc.

### Instruction Injection
Four templates are rendered and injected into `.github/instructions/` (except `copilot-instructions.md` which goes to `.github/`):

| File | Condition | Tokens | Purpose |
|------|-----------|--------|---------|
| `safety.instructions.md` | Always | ~60 | Banned files, safety rules |
| `git-workflow.instructions.md` | Always | ~90 | Branch naming, commit format, PR workflow |
| `testing.instructions.md` | Test runner detected | ~170 | How to run tests, import patterns |
| `copilot-instructions.md` | Always | ~350 | Completion checklist, workspace context |

### Tool Profiles
Profiles define which MCP servers and custom agents are available for a project. Built-in profiles:

| Profile | MCP Servers | Use Case |
|---------|-------------|----------|
| `base` | None | General development, no specialized tools |
| `oncall` | icm, ado-afd, adx, msdocs, enghub | Incident investigation and resolution |
| `azure` | ado, adx, msdocs | Azure infrastructure and services |
| `docs` | msdocs, enghub, context7 | Documentation and knowledge base |

Each profile is a `ToolProfile` containing:
- `name`: Profile identifier
- `mcp_servers`: List of MCPServer configs (command, args, env, tools_filter)
- `custom_agents`: List of agent names (reserved for future use)
- `env_vars`: Dict of environment variables

### Skill Bundles
Collections of related tools, agents, templates, and environment variables. Key bundles:

| Bundle | Servers | Agents | Purpose |
|--------|---------|--------|---------|
| `oncall` | icm, ado-afd, adx, msdocs, enghub | — | Incident investigation |
| `azure-dev` | ado, adx, msdocs | — | Azure development |
| `web-dev` | msdocs, enghub, context7 | — | Web development & docs |
| `testing` | — | — | Test runner & coverage rules |

Bundles can be composed with `compose_bundles(bundle_names...)` to merge MCP servers, agents, and environment variables.

### Project Profiles Registry (profiles.yaml)
The `profiles.yaml` file maps projects to tool profiles:

```yaml
projects:
  my-project:
    profile: oncall
    description: On-call incident management
  
  data-pipeline:
    profile: azure
    description: Azure data infrastructure
```

Used by `ProjectProfileRegistry` to:
- Map project names to profiles
- Load available MCP servers for a project
- Generate `mcp-config.json` for Copilot CLI

## Command-Line Usage

### Basic Injection

```bash
python -m agent_context inject /workspace
```

Analyzes workspace, renders templates, writes to `.github/instructions/`.

### With Task Context

```bash
python -m agent_context inject /workspace \
  --task-id fix-auth \
  --task-desc "Add JWT token refresh" \
  --feedback "Missing error handling for expired tokens"
```

Task context is rendered into instruction templates, helping agents understand what's expected.

### With Tool Profile

```bash
python -m agent_context inject /workspace \
  --profile oncall
```

Generates `mcp-config.json` in workspace with MCP server configurations from the `oncall` profile.

### Full Example

```bash
python -m agent_context inject /workspace \
  --task-id ctx-readme-update \
  --task-desc "Rewrite README with architecture, examples, docs" \
  --acceptance-criteria "Cover all features, add architecture diagram" \
  --feedback "Critical: missing agent manifests, no architecture diagram" \
  --profile base \
  --overwrite
```

### CLI Options

```
inject WORKSPACE [options]
  --task-id TEXT                 Task identifier
  --task-desc TEXT               Task description
  --acceptance-criteria TEXT     What must be done
  --feedback TEXT                Previous review feedback
  --project-id TEXT              Project identifier
  --profile {base|oncall|azure|docs}  Tool profile name
  --overwrite                    Overwrite existing instruction files
  --verbose, -v                  Debug logging
```

## Python API Usage

### Simple Injection

```python
from agent_context import inject

status = inject("/workspace")
print(status)
# {
#   "safety.instructions.md": "written",
#   "git-workflow.instructions.md": "written",
#   "testing.instructions.md": "written",
#   "copilot-instructions.md": "written"
# }
```

### With Task Context

```python
from agent_context import inject

task_context = {
    "task_id": "fix-auth",
    "description": "Add JWT token refresh endpoint",
    "feedback": "Missing error handling for expired tokens",
    "acceptance_criteria": "Handle refresh failures gracefully"
}

status = inject("/workspace", task_context=task_context)
```

### With Profile (MCP Config Generation)

```python
from agent_context import inject

status = inject("/workspace", profile_name="oncall")

if "mcp_config_path" in status:
    print(f"MCP config written to: {status['mcp_config_path']}")
```

### Working with Profiles

```python
from agent_context import get_profile, BUILTIN_PROFILES

# Get a specific profile
oncall_profile = get_profile("oncall")
print(f"MCP servers: {[s.name for s in oncall_profile.mcp_servers]}")

# List all profiles
print("Available profiles:", list(BUILTIN_PROFILES.keys()))
```

### Working with Skill Bundles

```python
from agent_context import (
    get_bundle, 
    list_bundle_names, 
    compose_bundles
)

# Get a single bundle
oncall = get_bundle("oncall")
print(f"Servers: {[s.name for s in oncall.mcp_servers]}")

# List all bundles
print("Available bundles:", list_bundle_names())

# Compose multiple bundles
combined = compose_bundles("oncall", "azure-dev")
print(f"Combined servers: {[s.name for s in combined.mcp_servers]}")
```

### Project Profile Registry

```python
from agent_context.profile_loader import ProjectProfileRegistry

# Load from profiles.yaml
registry = ProjectProfileRegistry.from_file("profiles.yaml")

# Get profile for a project
profile = registry.get_project_profile("my-project")
if profile:
    print(f"Project uses: {profile.name}")
    print(f"MCP servers: {[s.name for s in profile.mcp_servers]}")

# List all projects
print("Projects:", registry.list_projects())

# See which profiles are used
print("Profiles in use:", registry.list_profiles_used())
```

## Tool Profile Format

Tool profiles define available MCP servers and agents for a project.

### Profile Structure

```python
@dataclass
class ToolProfile:
    name: str                              # e.g., "oncall", "azure", "base"
    mcp_servers: list[MCPServer] = []      # MCP server configurations
    custom_agents: list[str] = []          # Agent names (reserved for future use)
    env_vars: dict[str, str] = {}          # Environment variables
```

### MCPServer Structure

```python
@dataclass
class MCPServer:
    name: str                              # e.g., "icm", "ado-afd", "adx"
    command: str                           # e.g., "mcp-icm"
    args: list[str] = []                   # Arguments to command
    env: dict[str, str] = {}               # Server-specific env vars
    tools_filter: Optional[list[str]] = None  # Only expose these tools (reserved for future use)
```

### Example Profile Definition

```python
from agent_context import MCPServer, ToolProfile

oncall_profile = ToolProfile(
    name="oncall",
    mcp_servers=[
        MCPServer(
            name="icm",
            command="mcp-icm",
            args=[],
            env={"ICM_API": "https://api.icm.microsoft.com"},
        ),
        MCPServer(
            name="ado-afd",
            command="mcp-ado-afd",
            args=["--verbose"],
            env={},
        ),
    ],
    custom_agents=[],  # Reserved for future use
    env_vars={"LOG_LEVEL": "DEBUG"},
)
```

### profiles.yaml Format

```yaml
# Map projects to tool profiles
projects:
  <project-name>:
    profile: <profile-name>           # base, oncall, azure, docs
    description: <optional>
    
  agent-context:
    profile: base
    description: Context injection system
    
  incident-manager:
    profile: oncall
    description: On-call incident management
    
  azure-data-lake:
    profile: azure
    description: Azure data infrastructure
```

## Skill Bundle Format

Skill bundles are collections of MCP servers, agents, templates, and environment variables.

### Bundle Structure

```python
@dataclass
class SkillBundle:
    name: str
    description: str = ""
    mcp_servers: list[MCPServer] = []
    custom_agents: list[str] = []
    instruction_templates: list[str] = []  # Reserved for future use
    env_vars: dict[str, str] = {}
```

### Example Bundle

```python
from agent_context import SkillBundle, MCPServer

testing_bundle = SkillBundle(
    name="testing",
    description="Test execution and coverage guidelines",
    mcp_servers=[],
    custom_agents=[],  # Reserved for future use
    instruction_templates=[],  # Reserved for future use
    env_vars={"PYTHONPATH": "src/"},
)
```

### Composing Bundles

```python
from agent_context import compose_bundles

# Merge multiple bundles
combined = compose_bundles("oncall", "azure-dev")
# Result: MCP servers from oncall + azure-dev agents + merged env_vars
```

## MCP Config Generation

When you specify a `--profile`, agent-context generates `mcp-config.json` in the workspace root.

### Generated Format

```json
{
  "mcpServers": {
    "icm": {
      "command": "mcp-icm",
      "args": [],
      "env": {}
    },
    "ado-afd": {
      "command": "mcp-ado-afd",
      "args": [],
      "env": {}
    }
  },
  "env": {
    "LOG_LEVEL": "DEBUG"
  }
}
```

This file is read by Copilot CLI to enable MCP servers for agents.

### Usage

```bash
# Generate mcp-config.json for oncall profile
python -m agent_context inject /workspace --profile oncall

# Result: creates or updates /workspace/mcp-config.json
```

## Integration with Dispatcher

In your K8s Job setup, inject instructions before running Copilot:

```bash
#!/bin/bash

export WORKSPACE=/workspace
export TASK_ID=fix-auth
export PROFILE=base

# 1. Inject workspace-aware instructions
python -m agent_context inject "$WORKSPACE" \
  --task-id "$TASK_ID" \
  --profile "$PROFILE" \
  --verbose

# 2. Check status
if [ $? -ne 0 ]; then
  echo "Instruction injection failed"
  exit 1
fi

# 3. Run agent with Copilot CLI
PROMPT="Fix authentication error handling"
copilot -p "$PROMPT" --allow-all

# 4. Capture result
EXIT_CODE=$?
exit $EXIT_CODE
```

## Generated Instruction Files

### safety.instructions.md (~60 tokens)

Lists banned files and safety rules. Example:

```markdown
# Safety Rules

Do NOT commit:
- API keys, credentials, secrets
- node_modules/, __pycache__/, .venv/
- Build artifacts (.o, .class, dist/)
- IDE settings (.idea/, .vscode/)
- Local config files (.env, config.local.json)
```

### git-workflow.instructions.md (~90 tokens)

Git workflow rules for the project. Example:

```markdown
# Git Workflow

## Branch Naming
- Feature: feature/issue-123-description
- Bugfix: bugfix/issue-123-description
- Docs: docs/update-readme

## Commits
- Format: "type: description" (e.g., "feat: add JWT refresh")
- Sign: git commit -S -m "..."

## Pull Requests
- Title must reference issue: "Fix #123: description"
- Run tests before creating PR
- Link acceptance criteria in description
```

### testing.instructions.md (~170 tokens)

How to run tests for the detected framework. Example:

```markdown
# Testing

## Running Tests
python -m pytest tests/ -v    # All tests
pytest tests/test_auth.py     # Single file
pytest -k test_login          # By name

## Before Committing
1. Run full test suite
2. Check code coverage (>80%)
3. Run linter: ruff check src/ tests/
4. Commit only if tests pass
```

### copilot-instructions.md (~350 tokens)

Main guidance file. Contains:
- Detected workspace context (languages, frameworks, test runner)
- How to verify changes (test/lint commands)
- Completion checklist addressing top failure modes
- Task-specific guidance (if task context provided)

Example checklist:

```markdown
# Completion Checklist

Before marking work complete, verify:
- ✓ All acceptance criteria met
- ✓ No placeholder text or TODO comments left
- ✓ Code changes tested (run: pytest tests/)
- ✓ New tests added for new functionality
- ✓ Documentation updated if APIs changed
- ✓ Git history is clean (proper commit messages)
- ✓ All files are saved and no debugging code left
```

## Installation

### From Source

```bash
git clone https://github.com/YotamNordman/agent-context.git
cd agent-context
pip install -e .
```

### With UV (Recommended)

```bash
uv pip install -e .
```

### With Poetry

```bash
poetry install
```

## Development

### Running Tests

```bash
# Run all tests with pytest
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_analyzer.py -v

# Run with coverage
uv run pytest tests/ --cov=src/agent_context
```

### Linting and Formatting

```bash
# Lint with ruff
uv run ruff check src/ tests/

# Format with ruff
uv run ruff format src/ tests/
```

### Running the CLI

```bash
# Full injection
python -m agent_context inject /tmp/test-workspace \
  --task-id test-task \
  --profile oncall \
  -v

# Check generated files
ls /tmp/test-workspace/.github/instructions/
```

## Testing Details

- **Unit tests**: 23 tests covering analyzer, injector, profiles, skills
- **Integration tests**: Profile loading, mcp-config generation
- **Time**: <1 second total
- **Coverage**: >90% of core logic

## What It Does NOT Do

- ✗ Make LLM calls — pure file analysis + Jinja2 templating
- ✗ Enforce style guides — agents know Python/JS conventions
- ✗ Provide framework tutorials — only project-specific commands
- ✗ Handle orchestration — this is context injection, not task planning
- ✗ Create or define agent manifests — custom_agents is reserved for future use

## Troubleshooting

### No instruction files generated

Check that `.github/instructions/` directory exists:

```bash
mkdir -p .github/instructions
python -m agent_context inject /workspace -v
```

### MCP config not generated

Ensure profile name is valid:

```bash
python -m agent_context inject /workspace --profile base -v
```

### Workspace not analyzed correctly

Run with verbose logging to see what was detected:

```bash
python -m agent_context inject /workspace -v
```

## License

MIT
