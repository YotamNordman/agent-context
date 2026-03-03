"""Injector — writes generated instruction files into the workspace."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .analyzer import analyze
from .profiles import ToolProfile, generate_mcp_config
from .renderer import render_instructions

logger = logging.getLogger(__name__)


def inject(
    workspace: str | Path,
    task_context: dict | None = None,
    overwrite: bool = False,
    profile: ToolProfile | None = None,
) -> dict[str, str]:
    """Analyze workspace and inject instruction files.

    Args:
        workspace: Path to the git workspace root.
        task_context: Optional dict with task_id, description, acceptance_criteria, feedback.
        overwrite: If True, overwrite existing instruction files. Default: only add missing.
        profile: Optional ToolProfile to use for MCP config generation.

    Returns:
        Dict of {filename: "written" | "skipped" | "error"} for each file.
    """
    workspace = Path(workspace)
    if not workspace.is_dir():
        raise ValueError(f"Workspace not found: {workspace}")

    info = analyze(workspace)
    rendered = render_instructions(info, task_context)

    # Generate MCP config if profile is provided
    if profile:
        project_id = task_context.get("project_id") if task_context else None
        mcp_config = generate_mcp_config(profile=profile, project_id=project_id)
        rendered["mcp-config.json"] = json.dumps(mcp_config, indent=2)

    instructions_dir = workspace / ".github" / "instructions"
    instructions_dir.mkdir(parents=True, exist_ok=True)

    status: dict[str, str] = {}

    for filename, content in rendered.items():
        if not content:
            status[filename] = "empty"
            continue

        if filename == "copilot-instructions.md":
            target = workspace / ".github" / "copilot-instructions.md"
        elif filename == "mcp-config.json":
            target = workspace / ".github" / "mcp-config.json"
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
