"""Injector — writes generated instruction files into the workspace."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from .analyzer import analyze
from .profiles import ToolProfile
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


def generate_mcp_config(
    workspace: str | Path,
    profile: ToolProfile,
    env_overrides: dict[str, str] | None = None,
) -> dict[str, str]:
    """Generate Copilot CLI mcp-config.json with only needed MCP servers.

    Generates a session-specific MCP configuration file in the Copilot CLI format.
    Includes environment variable substitution from the pod environment.

    Args:
        workspace: Path to the workspace root.
        profile: ToolProfile with MCP servers to include.
        env_overrides: Optional dict of environment variables to override or add.

    Returns:
        Dict of {filename: "written" | "error"} for mcp-config.json.
    """
    workspace = Path(workspace)
    if not workspace.is_dir():
        raise ValueError(f"Workspace not found: {workspace}")

    mcpServers = {}

    for server in profile.mcp_servers:
        # Substitute environment variables in command
        command = _substitute_env_vars(server.command, env_overrides)

        # Substitute environment variables in args
        args = [_substitute_env_vars(arg, env_overrides) for arg in server.args]

        # Merge server env with overrides
        merged_env = {**server.env}
        if env_overrides:
            merged_env.update(env_overrides)
        # Substitute env vars in values
        merged_env = {
            k: _substitute_env_vars(v, env_overrides)
            for k, v in merged_env.items()
        }

        server_config = {
            "type": "stdio",
            "command": command,
        }

        if args:
            server_config["args"] = args

        if merged_env:
            server_config["env"] = merged_env

        mcpServers[server.name] = server_config

    config = {"mcpServers": mcpServers}

    # Write to .copilot/mcp-config.json
    copilot_dir = workspace / ".copilot"
    copilot_dir.mkdir(parents=True, exist_ok=True)

    config_file = copilot_dir / "mcp-config.json"
    status: dict[str, str] = {}

    try:
        config_file.write_text(json.dumps(config, indent=2))
        status["mcp-config.json"] = "written"
        logger.info("Generated MCP config: %s", config_file)
    except OSError as e:
        status["mcp-config.json"] = f"error: {e}"
        logger.error("Failed to write %s: %s", config_file, e)

    return status


def _substitute_env_vars(
    value: str,
    overrides: dict[str, str] | None = None,
) -> str:
    """Substitute environment variables in a string using ${VAR} or $VAR syntax.

    Args:
        value: String that may contain ${VAR_NAME} or $VAR_NAME references.
        overrides: Optional dict of variables to check before pod environment.

    Returns:
        String with environment variables substituted.
    """
    if not value:
        return value

    result = value
    env_dict = {**os.environ, **(overrides or {})}

    # Handle ${VAR_NAME} syntax
    import re
    pattern_brace = r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}'
    result = re.sub(
        pattern_brace,
        lambda m: env_dict.get(m.group(1), m.group(0)),
        result,
    )

    # Handle $VAR_NAME syntax (only if not already part of another pattern)
    pattern_simple = r'\$([A-Za-z_][A-Za-z0-9_]*)'
    result = re.sub(
        pattern_simple,
        lambda m: env_dict.get(m.group(1), m.group(0)),
        result,
    )

    return result
