"""Injector — writes generated instruction files into the workspace."""

from __future__ import annotations

import logging
from pathlib import Path

from .analyzer import analyze
from .profiles import AgentDefinition, ToolProfile, get_agent, get_profile
from .renderer import render_instructions

logger = logging.getLogger(__name__)


def inject(
    workspace: str | Path,
    task_context: dict | None = None,
    overwrite: bool = False,
) -> dict[str, str]:
    """Analyze workspace and inject instruction files.

    Args:
        workspace: Path to the git workspace root.
        task_context: Optional dict with task_id, description, acceptance_criteria, feedback.
        overwrite: If True, overwrite existing instruction files. Default: only add missing.

    Returns:
        Dict of {filename: "written" | "skipped" | "error"} for each file.
    """
    workspace = Path(workspace)
    if not workspace.is_dir():
        raise ValueError(f"Workspace not found: {workspace}")

    info = analyze(workspace)
    rendered = render_instructions(info, task_context)

    instructions_dir = workspace / ".github" / "instructions"
    instructions_dir.mkdir(parents=True, exist_ok=True)

    status: dict[str, str] = {}

    for filename, content in rendered.items():
        if not content:
            status[filename] = "empty"
            continue

        if filename == "copilot-instructions.md":
            target = workspace / ".github" / "copilot-instructions.md"
        else:
            target = instructions_dir / filename

        if target.exists() and not overwrite:
            status[filename] = "skipped"
            logger.debug("Skipping existing: %s", target)
            continue

        try:
            target.write_text(content)
            status[filename] = "written"
            logger.info("Injected: %s", target)
        except OSError as e:
            status[filename] = f"error: {e}"
            logger.error("Failed to write %s: %s", target, e)

    written = sum(1 for v in status.values() if v == "written")
    skipped = sum(1 for v in status.values() if v == "skipped")
    logger.info("Injection complete: %d written, %d skipped", written, skipped)

    return status


def inject_custom_agents(
    workspace: str | Path,
    profile: str | ToolProfile,
    overwrite: bool = False,
) -> dict[str, str]:
    """Inject custom agent definition files based on a profile's agent list.

    Args:
        workspace: Path to the git workspace root.
        profile: Profile name (str) or ToolProfile object.
        overwrite: If True, overwrite existing agent files. Default: only
            add missing.

    Returns:
        Dict of {filename: "written" | "skipped" | "error" | "empty"} for each agent file.
        Empty means the agent was not found.
    """
    workspace = Path(workspace)
    if not workspace.is_dir():
        raise ValueError(f"Workspace not found: {workspace}")

    # Resolve profile
    if isinstance(profile, str):
        resolved_profile = get_profile(profile)
        if resolved_profile is None:
            raise ValueError(f"Profile not found: {profile}")
    else:
        resolved_profile = profile

    # Create agents directory
    agents_dir = workspace / ".copilot" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    status: dict[str, str] = {}

    for agent_name in resolved_profile.custom_agents:
        agent = get_agent(agent_name)
        if agent is None:
            status[f"{agent_name}.md"] = "empty"
            logger.warning("Agent not found: %s", agent_name)
            continue

        target = agents_dir / f"{agent_name}.md"

        if target.exists() and not overwrite:
            status[f"{agent_name}.md"] = "skipped"
            logger.debug("Skipping existing: %s", target)
            continue

        try:
            content = _format_agent_file(agent)
            target.write_text(content)
            status[f"{agent_name}.md"] = "written"
            logger.info("Injected agent: %s", target)
        except OSError as e:
            status[f"{agent_name}.md"] = f"error: {e}"
            logger.error("Failed to write %s: %s", target, e)

    written = sum(1 for v in status.values() if v == "written")
    skipped = sum(1 for v in status.values() if v == "skipped")
    logger.info("Agent injection complete: %d written, %d skipped", written, skipped)

    return status


def _format_agent_file(agent: AgentDefinition) -> str:
    """Format an agent definition as markdown content.

    Args:
        agent: AgentDefinition object.

    Returns:
        Formatted markdown content for the agent file.
    """
    lines = [
        f"# {agent.name}",
        "",
        f"{agent.description}",
        "",
        "## Instructions",
        "",
        agent.instructions,
        "",
    ]

    if agent.allowed_tools:
        lines.extend([
            "## Allowed Tools",
            "",
            ", ".join(agent.allowed_tools),
            "",
        ])

    if agent.mcp_servers:
        lines.extend([
            "## MCP Servers",
            "",
            ", ".join(agent.mcp_servers),
            "",
        ])

    return "\n".join(lines)
