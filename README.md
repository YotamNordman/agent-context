# agent-context

Deterministic context and tool injection for AI agent workspaces. Analyzes your workspace structure, detects languages, frameworks, and build tools, then generates tailored instruction files, tool profiles, and MCP server configurations. Agents get workspace-specific guidance without wasting context tokens.

## Overview

**agent-context** is a Python library for AI agent workspace setup. It:

1. **Analyzes** workspace structure: languages, frameworks, test runners, build tools, Docker/K8s manifests, CI configuration
2. **Generates** deterministic instruction files for Copilot CLI (safety, git workflow, testing, completion checklist)
3. **Injects** tool profiles and MCP server configurations for agent tool access
4. **Manages** skill bundles and custom agent definitions for multi-agent coordination
5. **Produces** claude_desktop_config.json for Claude Desktop or agent runtime consumption

No LLM calls—pure file analysis, Jinja2 templates, and dataclass configurations.

---

## Architecture

```
Workspace
    ↓
[Analyzer] → WorkspaceInfo {languages, frameworks, test_runner, ...}
    ↓
┌─────────────────────────┬────────────────────────┬──────────────────────┐
│                         │                        │                      │
[Renderer]            [ToolProfile]           [SkillBundle]       [MCPConfig]
    ↓                     ↓                        ↓                      ↓
Instruction         Tool Profiles &           Skill Bundles        MCP Server
Files             MCP Servers              Agent Manifests        Configuration
    ↓                     ↓                        ↓                      ↓
.github/             profiles.yaml         agent_manifest.json   claude_desktop_config.json
instructions/
```

**Data Flow:**
1. Analyzer examines `pyproject.toml`, `package.json`, `Dockerfile`, `.github/workflows`, etc.
2. Renderer uses Jinja2 templates with detected info to generate instruction files
3. Tool profiles define which MCP servers and custom agents are available
4. Skill bundles group related agents for multi-agent workflows
5. MCP config generator produces runtime-ready server configurations

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

Define which MCP servers and custom agents are available. Predefined profiles:

- **`base`** — No external tools (safe default)
- **`oncall`** — ICM, ADO, ADX, MS Docs, EngHub (incident response tools)
- **`azure`** — ADO, ADX, MS Docs (Azure/DevOps operations)
- **`docs`** — MS Docs, EngHub, Context7 (documentation tools)

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

### 4. Skill Bundles

Group related agents for multi-agent workflows. Predefined bundles include release pipelines, incident response, documentation, and engineering hub integrations.

**Example:**

```python
from agent_context import get_skill_bundle

bundle = get_skill_bundle("release-pipeline")
print(bundle.name)       # "release-pipeline"
print(bundle.agents)     # List of AgentDefinition objects
print(bundle.skills)     # Grouped agent skills

# Use in custom agent injection
from agent_context import inject_custom_agents
inject_custom_agents("/workspace", bundle=bundle)
```

### 5. MCP Config Generation

Generate `claude_desktop_config.json` or custom MCP runtime configs with environment variable substitution.

```python
from agent_context import generate_mcp_config

config = generate_mcp_config(
    profile_name="oncall",
    project_id="my-project"
)

# config is a dict ready for claude_desktop_config.json:
# {
#   "mcpServers": {
#     "icm": { "command": "mcp-icm", "args": [], "env": {} },
#     ...
#   }
# }
```

Environment variables are substituted (e.g., `${GITHUB_TOKEN}` → actual token value).

### 6. Agent Manifests

Define custom agents and their capabilities for multi-agent workflows.

```python
from agent_context import AgentDefinition, ToolProfile

agent = AgentDefinition(
    name="release-manager",
    description="Handles release automation",
    profile_name="azure",
    entry_point="./agents/release.py",
    timeout_seconds=3600,
)

# Agents are bundled in skill bundles for coordinated execution
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

#### Skill bundles

```python
from agent_context import get_skill_bundle

# Get predefined bundle
bundle = get_skill_bundle("release-pipeline")

if bundle:
    print(f"Bundle: {bundle.name}")
    print(f"Agents: {[a.name for a in bundle.agents]}")
    print(f"Skills: {list(bundle.skills.keys())}")

# List available bundles
from agent_context import BUILTIN_SKILL_BUNDLES

for name in BUILTIN_SKILL_BUNDLES:
    print(f"- {name}")
```

#### Custom agent injection

```python
from agent_context import inject_custom_agents, SkillBundle, AgentDefinition

# Inject agents from a skill bundle
status = inject_custom_agents(
    "/workspace",
    bundle=bundle,  # SkillBundle instance
)

# Or create custom agents
agents = [
    AgentDefinition(
        name="custom-agent",
        description="Does custom work",
        profile_name="base",
        entry_point="./agents/custom.py",
        timeout_seconds=1800,
    ),
]

# Inject custom agents (creates agent_manifest.json)
status = inject_custom_agents(
    "/workspace",
    agents=agents,
)
```

#### MCP config generation

```python
from agent_context import generate_mcp_config

# Generate from profile
config = generate_mcp_config(
    profile_name="oncall",
    project_id="my-project",
)

# config is ready for claude_desktop_config.json or runtime
# {
#   "mcpServers": {
#     "icm": {"command": "mcp-icm", ...},
#     ...
#   }
# }

# With environment variable substitution
config = generate_mcp_config(
    profile_name="azure",
    env_vars={"GITHUB_TOKEN": "ghp_xyz", "ADO_PAT": "..."}
)
```

### Integration with dispatcher

In K8s Job or container startup:

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

# Inject custom agents if needed
python -m agent_context inject_custom_agents /workspace \
  --bundle release-pipeline

# Now run the agent
copilot -p "$PROMPT" --allow-all
```

Or in Python:

```python
import subprocess
from agent_context import inject, inject_custom_agents

# Phase 1: Inject core instructions
inject(
    "/workspace",
    task_context={
        "task_id": task_id,
        "description": task_desc,
        "feedback": feedback,
    },
)

# Phase 2: Inject custom agents if multi-agent task
inject_custom_agents(
    "/workspace",
    bundle=bundle,
)

# Phase 3: Run agent
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

#### `inject_custom_agents(workspace, bundle=None, agents=None) → dict[str, str]`

Inject custom agent definitions and skill bundles.

**Parameters:**
- `workspace` (str | Path): Workspace root directory
- `bundle` (SkillBundle): Predefined skill bundle to inject
- `agents` (list[AgentDefinition]): Custom agents to inject

**Returns:** Dict of `{filename: "written" | "skipped" | "error"}`

#### `analyze(workspace) → WorkspaceInfo`

Analyze workspace structure and capabilities.

**Returns:** WorkspaceInfo with detected languages, frameworks, test runners, etc.

#### `get_profile(name: str) → ToolProfile | None`

Get a builtin tool profile by name.

**Parameters:**
- `name`: Profile name (e.g., "oncall", "azure", "docs", "base")

#### `get_skill_bundle(name: str) → SkillBundle | None`

Get a predefined skill bundle by name.

#### `get_agent(name: str) → AgentDefinition | None`

Get a predefined agent by name.

#### `generate_mcp_config(profile_name, project_id=None, env_vars=None) → dict`

Generate MCP server configuration from a profile.

**Parameters:**
- `profile_name`: Profile name (e.g., "oncall")
- `project_id`: Optional project identifier
- `env_vars`: Optional environment variable overrides

**Returns:** Dict ready for `claude_desktop_config.json`

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

Tool and agent configuration.

**Attributes:**
- `name` (str): Profile identifier
- `mcp_servers` (list[MCPServer]): MCP server configurations
- `custom_agents` (list[str]): Agent IDs to include
- `env_vars` (dict[str, str]): Environment variables

#### `MCPServer`

MCP server configuration.

**Attributes:**
- `name` (str): Server name
- `command` (str): Command to execute
- `args` (list[str]): Command arguments
- `env` (dict[str, str]): Environment variables
- `tools_filter` (list[str] | None): Specific tools to expose

#### `SkillBundle`

Grouped agents and related skills.

**Attributes:**
- `name` (str): Bundle identifier
- `agents` (list[AgentDefinition]): Agents in bundle
- `skills` (dict[str, list[str]]): Grouped agent capabilities

#### `AgentDefinition`

Custom agent definition.

**Attributes:**
- `name` (str): Agent name
- `description` (str): Agent purpose
- `profile_name` (str): Tool profile this agent uses
- `entry_point` (str): Python file or executable path
- `timeout_seconds` (int): Execution timeout

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

### Example 2: Multi-agent release workflow

```python
from agent_context import inject, inject_custom_agents, get_skill_bundle

# Setup workspace
inject(
    "/workspace",
    task_context={"task_id": "release-1.0.0"},
)

# Add release pipeline agents
bundle = get_skill_bundle("release-pipeline")
inject_custom_agents("/workspace", bundle=bundle)

# Now `agent_manifest.json` contains agents:
# - release-manager (verifies changelog, bumps version)
# - test-coordinator (runs full test suite)
# - changelog-validator (ensures CHANGELOG is updated)
# - git-coordinator (creates release tag and PR)
```

Each agent has its own tool profile and can run in parallel or sequence.

### Example 3: K8s deployment in CI/CD

```bash
#!/bin/bash
set -e

export TASK_ID="deploy-staging"
export PROFILE="azure"

# Inject workspace context
python -m agent_context inject /workspace \
  --task-id "$TASK_ID" \
  --profile "$PROFILE"

# Generate MCP config for agent runtime
python -c "
from agent_context import generate_mcp_config
import json

config = generate_mcp_config('$PROFILE')
with open('mcp-config.json', 'w') as f:
    json.dump(config, f, indent=2)
"

# Deploy
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
