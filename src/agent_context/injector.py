"""Injector — writes generated instruction files into the workspace."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .analyzer import analyze
from .profiles import get_profile
from .renderer import render_instructions

logger = logging.getLogger(__name__)


def _profile_to_mcp_config(profile_name: str) -> dict:
    """Convert a ToolProfile to mcp-config.json format."""
    profile = get_profile(profile_name)
    if not profile:
        return {}

    config = {
        "mcpServers": {},
        "env": profile.env_vars or {},
    }

    for server in profile.mcp_servers:
        config["mcpServers"][server.name] = {
            "command": server.command,
            "args": server.args or [],
            "env": server.env or {},
        }
        if server.tools_filter:
            config["mcpServers"][server.name]["tools_filter"] = server.tools_filter

    return config


def inject(
    workspace: str | Path,
    task_context: dict | None = None,
    overwrite: bool = False,
    profile_name: str | None = None,
) -> dict[str, str]:
    """Analyze workspace and inject instruction files.

    Args:
        workspace: Path to the git workspace root.
        task_context: Optional dict with task_id, description, acceptance_criteria, feedback.
        overwrite: If True, overwrite existing instruction files. Default: only add missing.
        profile_name: Optional tool profile name to generate mcp-config.json.

    Returns:
        Dict of {filename: "written" | "skipped" | "error"} for each file,
        plus optional "mcp_config_path" key with path to generated mcp-config.json.
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

    # Generate mcp-config.json if profile is specified
    if profile_name:
        mcp_config = _profile_to_mcp_config(profile_name)
        if mcp_config:
            mcp_config_path = workspace / "mcp-config.json"
            try:
                mcp_config_path.write_text(json.dumps(mcp_config, indent=2))
                status["mcp-config.json"] = "written"
                status["mcp_config_path"] = str(mcp_config_path)
                logger.info("Wrote mcp-config.json: %s", mcp_config_path)
            except OSError as e:
                status["mcp-config.json"] = f"error: {e}"
                logger.error("Failed to write mcp-config.json: %s", e)
        else:
            logger.warning("Profile not found or empty: %s", profile_name)
            status["mcp-config.json"] = "skipped"

    written = sum(1 for v in status.values() if v == "written")
    skipped = sum(1 for v in status.values() if v == "skipped")
    logger.info("Injection complete: %d written, %d skipped", written, skipped)

    return status
