# agent-context

Deterministic context injection for AI agent workspaces. Generates `.github/instructions/*.instructions.md` files before Copilot CLI runs so agents get high-quality, workspace-specific guidance without wasting context tokens on things they already know.

## What it does

1. **Analyzes** the workspace: detects language, framework, test runner, build tools
2. **Renders** only the instruction files that matter for that workspace
3. **Injects** them into `.github/instructions/` — Copilot CLI reads these automatically

## What it does NOT do

- No LLM calls — pure file analysis + Jinja2 templates
- No style guides — the agent already knows Python/JS/Docker conventions
- No framework tutorials — just the project-specific commands and rules
- No task planning — this is context, not orchestration

## Why it exists

Analysis of 20 review rejections showed agents fail because of:
- **Incomplete work** (declared done at 30-60%)
- **Placeholder content** left in (`[INSERT X]`, `TODO`)
- **References to non-existent files** in docs
- **Not running tests** before committing

The injected instructions include a **completion checklist** that directly addresses these failure modes in ~670 tokens (vs ~2,000 tokens for style guides that don't help).

## Usage

```bash
# CLI
python -m agent_context inject /workspace --task-id fix-auth --feedback "Missing error handling"

# Python API
from agent_context import inject
inject("/workspace", task_context={"task_id": "fix-auth", "feedback": "..."})
```

## Project Profiles

### profiles.yaml

The `profiles.yaml` file at the repository root maps each project to its tool profile. This determines which MCP servers and custom agents are available for agents working on that project.

**Format:**
```yaml
projects:
  <project-name>:
    profile: <profile-name>
    description: <optional description>
```

**Available Profiles:**
- `base` — Minimal tools for general development (no specialized MCP servers)
- `oncall` — On-call support with ICM, ADO-AFD, ADX, MSDocs, EngHub servers
- `azure` — Azure-focused tools with ADO, ADX, MSDocs servers  
- `docs` — Documentation tools with MSDocs, EngHub, Context7 servers

**Example:**
```yaml
projects:
  agent-context:
    profile: base
    description: Workspace context injection system

  datapipelines:
    profile: azure
    description: Azure-focused data processing
```

See `profiles.py` for detailed server configurations.

## Integration with dispatcher

In the K8s Job setup command, add before `copilot` runs:

```bash
python -m agent_context inject /workspace --task-id $TASK_ID && copilot -p "$PROMPT" --allow-all
```

## Templates injected

| File | When | Tokens | Content |
|------|------|--------|---------|
| `safety.instructions.md` | Always | ~60 | Banned files list |
| `git-workflow.instructions.md` | Always | ~90 | Branch + commit + PR rules |
| `testing.instructions.md` | Test runner detected | ~170 | Run command, import patterns |
| `copilot-instructions.md` | Always | ~350 | Stack, verify commands, completion checklist |

## Install

```bash
pip install -e .
```

## Test

```bash
uv run pytest tests/ -v   # 23 tests, <1 second
uv run ruff check src/ tests/
```
