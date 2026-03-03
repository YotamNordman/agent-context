"""Tool profiles — predefined configurations for MCP servers and custom agents."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MCPServer:
    """Configuration for a Model Context Protocol server."""

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    tools_filter: Optional[list[str]] = None


@dataclass
class ToolProfile:
    """Configuration profile for tools, MCP servers, and custom agents."""

    name: str
    mcp_servers: list[MCPServer] = field(default_factory=list)
    custom_agents: list[str] = field(default_factory=list)
    env_vars: dict[str, str] = field(default_factory=dict)


# Predefined MCP server configurations
_SERVERS = {
    "icm": MCPServer(
        name="icm",
        command="mcp-icm",
        args=[],
        env={},
    ),
    "ado-afd": MCPServer(
        name="ado-afd",
        command="mcp-ado-afd",
        args=[],
        env={},
    ),
    "adx": MCPServer(
        name="adx",
        command="mcp-adx",
        args=[],
        env={},
    ),
    "msdocs": MCPServer(
        name="msdocs",
        command="mcp-msdocs",
        args=[],
        env={},
    ),
    "enghub": MCPServer(
        name="enghub",
        command="mcp-enghub",
        args=[],
        env={},
    ),
    "ado": MCPServer(
        name="ado",
        command="mcp-ado",
        args=[],
        env={},
    ),
    "context7": MCPServer(
        name="context7",
        command="mcp-context7",
        args=[],
        env={},
    ),
}

# Predefined tool profiles
BUILTIN_PROFILES = {
    "base": ToolProfile(
        name="base",
        mcp_servers=[],
        custom_agents=[],
        env_vars={},
    ),
    "oncall": ToolProfile(
        name="oncall",
        mcp_servers=[
            _SERVERS["icm"],
            _SERVERS["ado-afd"],
            _SERVERS["adx"],
            _SERVERS["msdocs"],
            _SERVERS["enghub"],
        ],
        custom_agents=[],
        env_vars={},
    ),
    "azure": ToolProfile(
        name="azure",
        mcp_servers=[
            _SERVERS["ado"],
            _SERVERS["adx"],
            _SERVERS["msdocs"],
        ],
        custom_agents=[],
        env_vars={},
    ),
    "docs": ToolProfile(
        name="docs",
        mcp_servers=[
            _SERVERS["msdocs"],
            _SERVERS["enghub"],
            _SERVERS["context7"],
        ],
        custom_agents=[],
        env_vars={},
    ),
}


def get_profile(name: str) -> ToolProfile | None:
    """Get a profile by name, or None if not found."""
    profile = BUILTIN_PROFILES.get(name)
    if profile is not None:
        return copy.deepcopy(profile)
    return None


def generate_mcp_config(
    profile: ToolProfile | None = None,
    project_id: str | None = None,
) -> dict:
    """Generate MCP configuration from a profile.

    Args:
        profile: ToolProfile to generate config from. If None, returns empty config.
        project_id: Optional project identifier for context.

    Returns:
        Dict with mcp_servers, custom_agents, and env_vars keys.
    """
    if profile is None:
        return {
            "mcp_servers": [],
            "custom_agents": [],
            "env_vars": {},
            "project_id": project_id,
        }

    config = {
        "profile_name": profile.name,
        "mcp_servers": [
            {
                "name": server.name,
                "command": server.command,
                "args": server.args,
                "env": server.env,
                "tools_filter": server.tools_filter,
            }
            for server in profile.mcp_servers
        ],
        "custom_agents": profile.custom_agents,
        "env_vars": profile.env_vars,
    }

    if project_id:
        config["project_id"] = project_id

    return config
