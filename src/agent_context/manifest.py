"""Manifest generator — outputs JSON describing the complete agent session configuration."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .analyzer import analyze, WorkspaceInfo
from .profiles import ToolProfile, get_profile
from .renderer import render_instructions

logger = logging.getLogger(__name__)


@dataclass
class ManifestData:
    """Complete configuration manifest for an agent session."""

    workspace: str
    profile_name: str
    task_context: dict[str, Any]
    instructions: dict[str, str]
    mcp_servers: list[dict[str, Any]]
    custom_agents: list[str]
    env_vars: dict[str, str]
    workspace_info: dict[str, Any]
    estimated_context_tokens: int


def generate_manifest(
    workspace: str | Path,
    profile: str | ToolProfile | None = None,
    task_context: dict[str, Any] | None = None,
) -> ManifestData:
    """Generate a complete manifest describing the agent session configuration.

    This manifest is used by the dispatcher to configure the Kubernetes pod correctly.
    It includes all instructions, MCP servers, custom agents, environment variables,
    and estimated context tokens.

    Args:
        workspace: Path to the workspace root.
        profile: Tool profile name (str) or ToolProfile object. If None, uses 'base'.
        task_context: Optional dict with task_id, description, acceptance_criteria, feedback.

    Returns:
        ManifestData object containing all configuration.

    Raises:
        ValueError: If workspace doesn't exist or profile is invalid.
    """
    workspace = Path(workspace)
    if not workspace.is_dir():
        raise ValueError(f"Workspace not found: {workspace}")

    # Resolve profile
    profile_name: str
    tool_profile: ToolProfile
    if profile is None:
        profile_name = "base"
        tool_profile = _get_profile_or_default("base")
    elif isinstance(profile, str):
        profile_name = profile
        tool_profile = _get_profile_or_default(profile)
    elif isinstance(profile, ToolProfile):
        profile_name = profile.name
        tool_profile = profile
    else:
        raise ValueError(f"Invalid profile type: {type(profile)}")

    # Analyze workspace
    info = analyze(workspace)

    # Render instructions
    instructions = render_instructions(info, task_context)

    # Build MCP servers list
    mcp_servers = [
        {
            "name": server.name,
            "command": server.command,
            "args": server.args,
            "env": server.env,
            "tools_filter": server.tools_filter,
        }
        for server in tool_profile.mcp_servers
    ]

    # Build environment variables
    env_vars = dict(tool_profile.env_vars)

    # Estimate context tokens (heuristic based on rendered content + workspace info)
    estimated_tokens = _estimate_context_tokens(
        instructions, mcp_servers, info, task_context or {}
    )

    # Build workspace info for manifest
    workspace_info_dict = asdict(info)
    workspace_info_dict["path"] = str(workspace_info_dict["path"])

    manifest = ManifestData(
        workspace=str(workspace),
        profile_name=profile_name,
        task_context=task_context or {},
        instructions=instructions,
        mcp_servers=mcp_servers,
        custom_agents=tool_profile.custom_agents,
        env_vars=env_vars,
        workspace_info=workspace_info_dict,
        estimated_context_tokens=estimated_tokens,
    )

    logger.info(
        "Generated manifest for workspace=%s profile=%s tokens=%d",
        workspace,
        profile_name,
        estimated_tokens,
    )

    return manifest


def manifest_to_dict(manifest: ManifestData) -> dict[str, Any]:
    """Convert ManifestData to a dictionary (for JSON serialization)."""
    return asdict(manifest)


def manifest_to_json(manifest: ManifestData, indent: int | None = 2) -> str:
    """Convert ManifestData to JSON string.

    Args:
        manifest: The manifest to serialize.
        indent: JSON indentation level. None for compact output.

    Returns:
        JSON string representation of the manifest.
    """
    return json.dumps(manifest_to_dict(manifest), indent=indent)


def _get_profile_or_default(name: str) -> ToolProfile:
    """Get a profile by name, or raise ValueError if not found."""
    profile = get_profile(name)
    if profile is None:
        raise ValueError(f"Unknown profile: {name}")
    return profile


def _estimate_context_tokens(
    instructions: dict[str, str],
    mcp_servers: list[dict[str, Any]],
    workspace_info: WorkspaceInfo,
    task_context: dict[str, Any],
) -> int:
    """Estimate context tokens needed for the agent session.

    This uses a heuristic calculation:
    - ~1 token per 4 characters of instruction content
    - Base overhead for MCP servers, workspace info, task context
    - Estimates work best when instructions are typical length

    Args:
        instructions: Dict of instruction filename -> content
        mcp_servers: List of MCP server configs
        workspace_info: Detected workspace characteristics
        task_context: Task context dict

    Returns:
        Estimated number of tokens.
    """
    # Count tokens from instructions (~1 token per 4 chars)
    instruction_text = "\n".join(instructions.values())
    instruction_tokens = len(instruction_text) // 4

    # Base overhead: ~100 tokens for manifest structure and metadata
    base_tokens = 100

    # MCP server overhead: ~50 tokens per server
    mcp_tokens = len(mcp_servers) * 50

    # Workspace info: ~200 tokens
    workspace_tokens = 200

    # Task context: ~1 token per 4 chars
    task_text = json.dumps(task_context)
    task_tokens = len(task_text) // 4

    total = base_tokens + instruction_tokens + mcp_tokens + workspace_tokens + task_tokens

    logger.debug(
        "Estimated context tokens: base=%d instr=%d mcp=%d ws=%d task=%d total=%d",
        base_tokens,
        instruction_tokens,
        mcp_tokens,
        workspace_tokens,
        task_tokens,
        total,
    )

    return total
