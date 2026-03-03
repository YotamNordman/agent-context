# agent-context

Deterministic context injection for AI agent workspaces. Analyzes your workspace structure, detects languages, frameworks, and build tools, then generates tailored instruction files and tool profiles. Agents get workspace-specific guidance without wasting context tokens.

## Overview

**agent-context** is a Python library for AI agent workspace setup. It:

1. **Analyzes** workspace structure: languages, frameworks, test runners, build tools, Docker/K8s manifests, CI configuration
2. **Generates** deterministic instruction files for Copilot CLI (safety, git workflow, testing, completion checklist)
3. **Provides** tool profiles for MCP server configuration definitions

No LLM calls—pure file analysis, Jinja2 templates, and dataclass configurations.

---

## Architecture

```
Workspace
    ↓
[Analyzer] → WorkspaceInfo {languages, frameworks, test_runner, ...}
    ↓
┌─────────────────────────┬────────────────────────┐
│                         │                        │
[Renderer]            [ToolProfile]                │
    ↓                     ↓                        │
Instruction         Tool Profiles &                │
Files             MCP Server Definitions          │
    ↓                     ↓                        │
.github/             profiles.yaml                │
instructions/                                     │
```

**Data Flow:**
1. Analyzer examines `pyproject.toml`, `package.json`, `Dockerfile`, `.github/workflows`, etc.
2. Renderer uses Jinja2 templates with detected info to generate instruction files
3. Tool profiles define MCP server configurations for external agent tooling

---

## Core Features

### 1. Workspace Analysis

Automatically detects:

- **Languages:** Python, JavaScript
- **Frameworks:** FastAPI, Django, Flask, React, Vue, Vite, aiosqlite
- **Test runners:** pytest, jest, vitest, playwright, uv
- **Build/lint tools:** ruff, npm scripts
- **Deployment:** Docker (Dockerfile detection), Kubernetes (k8s/helm manifests)
- **CI:** GitHub Actions, GitLab CI, Jenkins
- **Project structure:** Source dirs (`src/`, `./`), test dirs (`tests/`, `test/`, `__tests__/`)

**Example detection:**

```python
from agent_context import analyze
from pathlib import Path

info = analyze(Path("/workspace"))
print(info.languages)      # ['python']
print(info.frameworks)     # ['fastapi']
print(info.test_runner)    # 'pytest'
print(info.test_command)   # 'uv run pytest tests/ -v'
print(info.has_dockerfile) # True
```

### 2. Instruction Injection

Generates deterministic, workspace-aware instruction files in `.github/instructions/`:

| File | When | Tokens | Content |
|------|------|--------|---------|
| `safety.instructions.md` | Always | ~60 | Banned files, reserved paths |
| `git-workflow.instructions.md` | Always | ~90 | Branch naming, commit format, PR rules |
| `testing.instructions.md` | Test runner detected | ~170 | Test command, import patterns, test discovery |
| `copilot-instructions.md` | Always | ~350 | Stack overview, verify commands, completion checklist |

**Why this approach:**
Analysis of 20+ agent review rejections showed common failure modes:
- Incomplete work (declared done at 30-60%)
- Placeholder content (`[INSERT X]`, `TODO`)
- References to non-existent files in docs
- Not running tests before committing

The completion checklist directly prevents these in ~670 tokens (vs ~2,000 for generic style guides).

### 3. Tool Profiles

Define MCP server configurations for external agent tooling. Predefined profiles:

- **`base`** — No external tools (safe default)
- **`oncall`** — ICM, ADO, ADX, MS Docs, EngHub (incident response tools)
- **`azure`** — ADO, ADX, MS Docs (Azure/DevOps operations)
- **`docs`** — MS Docs, EngHub, Context7 (documentation tools)

**Note:** Tool profiles provide MCP server configuration templates. The actual servers and runtime integration are external to agent-context.

**Custom profiles** can be defined in `profiles.yaml`:

```yaml
profiles:
  my-custom:
    mcp_servers:
      - name: ado
        command: mcp-ado
        args: []
        env: {}
      - name: context7
        command: mcp-context7
        args: []
        env: {}
    custom_agents: []
    env_vars:
      GITHUB_TOKEN: ${GITHUB_TOKEN}
```

---

## Usage Guide

### CLI

```bash
# Basic injection — analyze workspace and inject instructions
python -m agent_context inject /workspace

# With task context
python -m agent_context inject /workspace \
  --task-id "auth-fix" \
  --task-desc "Implement JWT refresh" \
  --feedback "Missing token validation"

# With specific tool profile
python -m agent_context inject /workspace \
  --profile oncall \
  --project-id my-project

# Overwrite existing files
python -m agent_context inject /workspace --overwrite

# Verbose output
python -m agent_context inject /workspace --verbose
```

### Python API

#### Basic injection

```python
from agent_context import inject

status = inject(
    "/workspace",
    task_context={
        "task_id": "auth-fix",
        "description": "Implement JWT refresh token rotation",
        "acceptance_criteria": "Tests pass, no secrets in code",
        "feedback": "Previous attempt: missing token validation",
    },
    overwrite=False
)

print(status)
# {
#   "safety.instructions.md": "written",
#   "git-workflow.instructions.md": "written",
#   "testing.instructions.md": "written",
#   "copilot-instructions.md": "written",
# }
```

#### Workspace analysis

```python
from agent_context import analyze
from pathlib import Path

info = analyze(Path("/workspace"))

print(f"Languages: {', '.join(info.languages)}")
print(f"Frameworks: {', '.join(info.frameworks)}")
print(f"Test runner: {info.test_runner}")
print(f"Test command: {info.test_command}")
print(f"Lint command: {info.lint_command}")
print(f"Source dirs: {info.source_dirs}")
print(f"Test dirs: {info.test_dirs}")
print(f"Docker: {info.has_dockerfile}")
print(f"K8s: {info.has_k8s_manifests}")
print(f"CI: {info.has_ci}")
```

#### Tool profiles

```python
from agent_context import (
    BUILTIN_PROFILES,
    ToolProfile,
    MCPServer,
    get_profile,
)

# Use builtin profile
oncall_profile = get_profile("oncall")
print(f"Servers: {[s.name for s in oncall_profile.mcp_servers]}")

# Create custom profile
custom = ToolProfile(
    name="custom",
    mcp_servers=[
        MCPServer(
            name="my-server",
            command="my-mcp-server",
            args=["--config", "config.json"],
            env={"LOG_LEVEL": "debug"},
        ),
    ],
    custom_agents=["agent1", "agent2"],
    env_vars={"MY_VAR": "value"},
)

# All builtin profiles
for name, profile in BUILTIN_PROFILES.items():
    print(f"{name}: {len(profile.mcp_servers)} servers")
```

### Integration Example

In a container or script setup:

```bash
#!/bin/bash
set -e

# Analyze workspace and inject instructions
python -m agent_context inject /workspace \
  --task-id "$TASK_ID" \
  --task-desc "$TASK_DESC" \
  --feedback "$FEEDBACK" \
  --profile oncall \
  --project-id my-project

# Now run the agent with contextual instructions
copilot -p "$PROMPT" --allow-all
```

Or in Python:

```python
from agent_context import inject

# Phase 1: Inject core instructions
status = inject(
    "/workspace",
    task_context={
        "task_id": task_id,
        "description": task_desc,
        "feedback": feedback,
    },
)

# Check injection status
for file, status in status.items():
    print(f"{file}: {status}")

# Phase 2: Run agent with context
import subprocess
subprocess.run([
    "copilot",
    "-p", prompt,
    "--allow-all"
], check=True)
```

---

## Profile Format Reference

### Tool Profile (`profiles.yaml`)

```yaml
profiles:
  my-profile:
    mcp_servers:
      - name: ado
        command: mcp-ado
        args:
          - --organization
          - my-org
        env:
          ADO_PAT: ${ADO_PAT}
          LOG_LEVEL: debug
        tools_filter:  # Optional: filter to specific tools
          - work-items
          - pull-requests
    
    custom_agents:
      - agent-id-1
      - agent-id-2
    
    env_vars:
      MY_CUSTOM_VAR: value
      GITHUB_TOKEN: ${GITHUB_TOKEN}
```

**Field Reference:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mcp_servers[].name` | string | ✓ | Server identifier |
| `mcp_servers[].command` | string | ✓ | Executable or command to run |
| `mcp_servers[].args` | list[string] | | Command arguments |
| `mcp_servers[].env` | dict | | Environment variables |
| `mcp_servers[].tools_filter` | list[string] | | Tool names to expose (if supported) |
| `custom_agents` | list[string] | | Agent bundle/IDs to include |
| `env_vars` | dict | | Profile-level environment variables |

**Environment Variable Substitution:**
- `${VAR_NAME}` → replaced with environment variable value
- `${VAR_NAME:default}` → default value if not set
- Supports all profile definitions (MCP servers, custom agents)

### MCP Server Configuration (Output)

Generated `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "icm": {
      "command": "mcp-icm",
      "args": [],
      "env": {}
    },
    "ado": {
      "command": "mcp-ado",
      "args": ["--organization", "my-org"],
      "env": {
        "ADO_PAT": "***"
      }
    }
  }
}
```

---

## API Reference

### Main Functions

#### `inject(workspace, task_context=None, overwrite=False) → dict[str, str]`

Analyze workspace and inject instruction files.

**Parameters:**
- `workspace` (str | Path): Workspace root directory
- `task_context` (dict): Optional task metadata
  - `task_id`: Unique task identifier
  - `description`: Task description
  - `acceptance_criteria`: Task acceptance criteria
  - `feedback`: Previous review feedback
  - `project_id`: Project identifier
- `overwrite` (bool): If True, overwrite existing files

**Returns:** Dict of `{filename: "written" | "skipped" | "error"}`

#### `get_profile(name: str) → ToolProfile | None`

Get a builtin tool profile by name.

**Parameters:**
- `name`: Profile name (e.g., "oncall", "azure", "docs", "base")

#### `analyze(workspace) → WorkspaceInfo`

Analyze workspace structure and capabilities.

**Parameters:**
- `workspace` (str | Path): Workspace root directory

**Returns:** WorkspaceInfo with detected languages, frameworks, test runners, etc.

### Data Classes

#### `WorkspaceInfo`

Detected workspace characteristics.

**Attributes:**
- `languages` (list[str]): Detected languages
- `frameworks` (list[str]): Detected frameworks
- `test_runner` (str | None): Test runner name
- `test_command` (str | None): Command to run tests
- `lint_command` (str | None): Linting command
- `build_command` (str | None): Build command
- `has_dockerfile` (bool): Docker support
- `has_k8s_manifests` (bool): Kubernetes support
- `has_ci` (bool): CI/CD configuration present
- `source_dirs` (list[str]): Source code directories
- `test_dirs` (list[str]): Test directories
- `package_name` (str | None): Package/project name

#### `ToolProfile`

Tool configuration definition.

**Attributes:**
- `name` (str): Profile identifier
- `mcp_servers` (list[MCPServer]): MCP server configurations
- `custom_agents` (list[str]): Agent IDs (for future use)
- `env_vars` (dict[str, str]): Environment variables

#### `MCPServer`

MCP server configuration.

**Attributes:**
- `name` (str): Server name
- `command` (str): Command to execute
- `args` (list[str]): Command arguments
- `env` (dict[str, str]): Environment variables
- `tools_filter` (list[str] | None): Specific tools to expose

---

## Installation

### From PyPI

```bash
pip install agent-context
```

### Development

```bash
# Clone repository
git clone https://github.com/YotamNordman/agent-context
cd agent-context

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
uv run pytest tests/ -v

# Run linter
uv run ruff check src/ tests/
```

### Requirements

- Python 3.11+
- Jinja2 3.1+

---

## Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_profiles.py -v

# Run with coverage
uv run pytest tests/ --cov=src/agent_context

# Lint
uv run ruff check src/ tests/

# Format check
uv run ruff format --check src/ tests/
```

Test coverage: 23+ tests, all core functionality covered.

---

## Examples

### Example 1: FastAPI project with pytest

```bash
$ python -m agent_context inject /workspace/my-api --profile oncall

Analyzed /workspace/my-api: langs=['python'] frameworks=['fastapi'] tests='pytest'
Injected: .github/instructions/safety.instructions.md
Injected: .github/instructions/git-workflow.instructions.md
Injected: .github/instructions/testing.instructions.md (uv run pytest tests/ -v)
Injected: .github/copilot-instructions.md
```

Generated files guide agent on:
- Which files are off-limits
- Proper git workflow
- How to run tests: `uv run pytest tests/ -v`
- Completion checklist to verify work

### Example 2: JavaScript project with custom tool profile

```python
from agent_context import inject, ToolProfile, MCPServer

# Create custom profile for a React project
custom_profile = ToolProfile(
    name="frontend",
    mcp_servers=[
        MCPServer(
            name="github",
            command="mcp-github",
            args=["--org", "myorg"],
            env={"GITHUB_TOKEN": "${GITHUB_TOKEN}"}
        )
    ],
    custom_agents=[],  # Reserved for future use
    env_vars={"NODE_ENV": "development"}
)

# Use with injection
status = inject(
    "/workspace",
    task_context={
        "task_id": "component-update",
        "description": "Update React component",
        "feedback": "Add proper TypeScript types",
    }
)

print(status)
# {
#   "safety.instructions.md": "written",
#   "git-workflow.instructions.md": "written", 
#   "testing.instructions.md": "written",  # if test runner detected
#   "copilot-instructions.md": "written"
# }
```

### Example 3: Container deployment setup

```bash
#!/bin/bash
set -e

export TASK_ID="deploy-staging"
export PROFILE="azure"

# Inject workspace context
python -m agent_context inject /workspace \
  --task-id "$TASK_ID" \
  --profile "$PROFILE"

# Verify injection
ls -la .github/instructions/
# safety.instructions.md
# git-workflow.instructions.md 
# testing.instructions.md
# ../copilot-instructions.md

# Deploy with contextualized agent
kubectl apply -f k8s/
```

---

## How it works

1. **Workspace scan:** Examines project files (pyproject.toml, package.json, Dockerfile, .github/workflows, etc.)
2. **Detection:** Identifies languages, frameworks, test runners, build tools, deployment targets
3. **Template rendering:** Uses Jinja2 to generate instruction files with detected info
4. **File injection:** Writes `.github/instructions/*.md` and optional config files
5. **Agent consumption:** Copilot CLI automatically reads these files before task execution

All operations are **deterministic** — same workspace → same output.

---

## License

Apache-2.0

---

## Contributing

Issues, PRs, and feedback welcome: https://github.com/YotamNordman/agent-context
