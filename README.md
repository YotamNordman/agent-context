# agent-context

Deterministic context injection for AI agent workspaces. Analyzes your workspace and generates targeted `.github/instructions/*.instructions.md` files so agents get workspace-specific guidance without wasting context tokens.

## Features

### 🔍 Workspace Analysis
Automatically detects workspace characteristics:
- **Languages:** Python, JavaScript/TypeScript
- **Frameworks:** FastAPI, Django, Flask, React, Vue, Vite
- **Test runners:** pytest, Jest, Playwright, Vitest  
- **Build tools:** npm scripts, Docker, Kubernetes manifests
- **CI/CD:** GitHub Actions, GitLab CI, Jenkins

### 📝 Instruction Injection
Generates targeted instruction files based on workspace analysis:
- `safety.instructions.md` — file safety rules and banned paths
- `git-workflow.instructions.md` — branching, commits, PR workflow  
- `testing.instructions.md` — test commands and patterns (when test runner detected)
- `copilot-instructions.md` — completion checklist and verification steps

### ⚙️ Tool Profiles & MCP Config Generation
Predefined configurations for MCP (Model Context Protocol) servers:
- **base:** Minimal profile with no additional servers
- **oncall:** ICM, ADO-AFD, ADX, Microsoft Docs, EngHub
- **azure:** Azure DevOps, ADX, Microsoft Docs
- **docs:** Microsoft Docs, EngHub, Context7

When using `--profile`, automatically generates `mcp-config.json` with the selected profile's MCP server configurations.

## Quick Start

```bash
# Install
pip install -e .

# Analyze workspace and inject instructions
python -m agent_context inject /path/to/workspace

# With task context and MCP profile
python -m agent_context inject /workspace \
  --task-id fix-auth \
  --feedback "Missing error handling" \
  --acceptance-criteria "All tests pass" \
  --profile oncall
```

## Python API

```python
from agent_context import inject, get_profile

# Basic injection
status = inject("/workspace")
print(status)  # {"safety.instructions.md": "written", ...}

# With task context
task_context = {
    "task_id": "fix-auth", 
    "description": "Add JWT authentication",
    "feedback": "Missing error handling"
}
status = inject("/workspace", task_context=task_context)

# With tool profile (generates mcp-config.json)
status = inject("/workspace", profile_name="oncall")
print(status.get("mcp_config_path"))  # Path to generated mcp-config.json

# Get tool profile details
profile = get_profile("oncall")
print(f"Profile has {len(profile.mcp_servers)} MCP servers")
```

**Note:** The workspace analysis function is internal. Use `inject()` which performs analysis automatically.

## CLI Reference

```bash
# Basic usage
python -m agent_context inject <workspace>

# Full options
python -m agent_context inject <workspace> \
  --task-id <string> \
  --task-desc <string> \
  --acceptance-criteria <string> \
  --feedback <string> \
  --project-id <string> \
  --profile <profile_name> \
  --overwrite  # Replace existing files
  --verbose    # Debug logging
```

Available profiles: `base`, `oncall`, `azure`, `docs`

## Example Output

For a FastAPI + pytest project with profile:

```bash
$ python -m agent_context inject ./my-api --profile oncall
{
  "safety.instructions.md": "written",
  "git-workflow.instructions.md": "written", 
  "testing.instructions.md": "written",
  "copilot-instructions.md": "written",
  "mcp-config.json": "written",
  "mcp_config_path": "/path/to/my-api/mcp-config.json"
}
```

Generated `testing.instructions.md` includes:
```markdown
## Testing

Run tests: `uv run pytest tests/ -v`
Lint code: `uv run ruff check src/ tests/`

Import patterns: `from src.my_api import ...`
```

Generated `mcp-config.json` includes:
```json
{
  "mcpServers": {
    "icm": {
      "command": "mcp-icm",
      "args": []
    },
    "ado-afd": {
      "command": "mcp-ado-afd",
      "args": []
    }
  }
}
```

## Architecture

```
┌──────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Workspace  │───▶│    Analyzer     │───▶│  Instructions   │
│ (files/dirs) │    │   (detector)    │    │   Templates     │
└──────────────┘    └─────────────────┘    └─────────────────┘
                              │                      │
                              ▼                      ▼
                      ┌──────────────┐    ┌─────────────────┐
                      │ WorkspaceInfo│    │    Renderer     │
                      │ (dataclass)  │───▶│   (Jinja2)      │
                      └──────────────┘    └─────────────────┘
                                                   │
                                                   ▼
                                        ┌─────────────────┐
                                        │    Injector     │
                                        │(.github/files + │
                                        │ mcp-config.json)│
                                        └─────────────────┘
```

## Integration Examples

### With dispatcher
```bash
# In K8s Job setup command
python -m agent_context inject /workspace --task-id $TASK_ID --profile oncall \
  && copilot -p "$PROMPT" --allow-all
```

### CI/CD Pipeline
```yaml
- name: Inject context
  run: python -m agent_context inject . --profile base
- name: Run agent
  run: copilot fix-tests --allow-all
```

## Tool Profile Format

Tool profiles are defined in `profiles.py`:

```python
@dataclass
class MCPServer:
    name: str
    command: str  # Executable name
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    tools_filter: Optional[list[str]] = None

@dataclass  
class ToolProfile:
    name: str
    mcp_servers: list[MCPServer] = field(default_factory=list)
    custom_agents: list[str] = field(default_factory=list)
    env_vars: dict[str, str] = field(default_factory=dict)
```

## Testing

```bash
uv run pytest tests/ -v        # Run all tests
uv run ruff check src/ tests/  # Lint code
uv run ruff format .           # Format code
```

## Why This Approach Works

Traditional agent failures analyzed across 20 review rejections:
- **Incomplete work** (30-60% done, declared complete)
- **Placeholder content** (`[INSERT X]`, `TODO` left behind)  
- **Missing tests** (not running before commit)
- **Non-existent references** (docs linking to missing files)

Solution: **Targeted instructions** (~670 tokens) with completion checklists, not generic style guides (~2,000 tokens) that don't address core failure modes.

## Development

```bash
git clone https://github.com/YotamNordman/agent-context
cd agent-context
pip install -e .
uv run pytest tests/ -v
```