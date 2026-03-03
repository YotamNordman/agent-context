"""Skill bundles — predefined collections of MCP servers, agents, templates, and env vars."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from .profiles import MCPServer, ToolProfile


@dataclass
class SkillBundle:
    """A named collection of skills: MCP servers, agent definitions, templates, and env vars."""

    name: str
    description: str = ""
    mcp_servers: list[MCPServer] = field(default_factory=list)
    custom_agents: list[str] = field(default_factory=list)
    instruction_templates: list[str] = field(default_factory=list)
    env_vars: dict[str, str] = field(default_factory=dict)

    def to_tool_profile(self) -> ToolProfile:
        """Convert SkillBundle to ToolProfile for compatibility."""
        return ToolProfile(
            name=self.name,
            mcp_servers=copy.deepcopy(self.mcp_servers),
            custom_agents=copy.copy(self.custom_agents),
            env_vars=copy.copy(self.env_vars),
        )


# Reference to predefined MCP servers from profiles
_SERVERS = {
    "icm": MCPServer(name="icm", command="mcp-icm"),
    "ado-afd": MCPServer(name="ado-afd", command="mcp-ado-afd"),
    "adx": MCPServer(name="adx", command="mcp-adx"),
    "msdocs": MCPServer(name="msdocs", command="mcp-msdocs"),
    "enghub": MCPServer(name="enghub", command="mcp-enghub"),
    "ado": MCPServer(name="ado", command="mcp-ado"),
    "context7": MCPServer(name="context7", command="mcp-context7"),
}

# Predefined skill bundles
BUILTIN_BUNDLES = {
    "oncall": SkillBundle(
        name="oncall",
        description="ICM incident investigation skills — investigate and resolve on-call incidents",
        mcp_servers=[
            _SERVERS["icm"],
            _SERVERS["ado-afd"],
            _SERVERS["adx"],
            _SERVERS["msdocs"],
            _SERVERS["enghub"],
        ],
        custom_agents=[],
        instruction_templates=["incident-investigation", "incident-resolution"],
        env_vars={},
    ),
    "azure-dev": SkillBundle(
        name="azure-dev",
        description="ADO work items + Kusto queries for Azure development",
        mcp_servers=[
            _SERVERS["ado"],
            _SERVERS["adx"],
            _SERVERS["msdocs"],
        ],
        custom_agents=[],
        instruction_templates=["azure-workitems", "kusto-queries"],
        env_vars={},
    ),
    "web-dev": SkillBundle(
        name="web-dev",
        description="Context7 for docs lookup and web development",
        mcp_servers=[
            _SERVERS["msdocs"],
            _SERVERS["enghub"],
            _SERVERS["context7"],
        ],
        custom_agents=[],
        instruction_templates=["docs-lookup", "web-patterns"],
        env_vars={},
    ),
    "testing": SkillBundle(
        name="testing",
        description="Test runner detection and coverage rules",
        mcp_servers=[],
        custom_agents=[],
        instruction_templates=["test-runner-detection", "coverage-rules"],
        env_vars={"TEST_RUNNER": "auto", "COVERAGE_MIN": "80"},
    ),
}


def get_bundle(name: str) -> SkillBundle | None:
    """Get a bundle by name, or None if not found."""
    bundle = BUILTIN_BUNDLES.get(name)
    if bundle is not None:
        return copy.deepcopy(bundle)
    return None


def compose_bundles(*bundle_names: str) -> SkillBundle:
    """Compose multiple bundles into a single bundle.

    Merges MCP servers (unique by name), custom agents, instruction templates,
    and environment variables from all specified bundles.

    Args:
        *bundle_names: Names of bundles to compose.

    Returns:
        A new SkillBundle with merged content from all specified bundles.

    Raises:
        ValueError: If any bundle name is not found.
    """
    if not bundle_names:
        return SkillBundle(
            name="empty",
            description="Empty composed bundle",
        )

    bundles = []
    for name in bundle_names:
        bundle = get_bundle(name)
        if bundle is None:
            raise ValueError(f"Bundle '{name}' not found")
        bundles.append(bundle)

    # Merge servers by name to avoid duplicates
    servers_dict: dict[str, MCPServer] = {}
    for bundle in bundles:
        for server in bundle.mcp_servers:
            servers_dict[server.name] = copy.deepcopy(server)

    # Merge custom agents (preserving order, avoiding duplicates)
    agents_set = set()
    merged_agents = []
    for bundle in bundles:
        for agent in bundle.custom_agents:
            if agent not in agents_set:
                agents_set.add(agent)
                merged_agents.append(agent)

    # Merge instruction templates (preserving order, avoiding duplicates)
    templates_set = set()
    merged_templates = []
    for bundle in bundles:
        for template in bundle.instruction_templates:
            if template not in templates_set:
                templates_set.add(template)
                merged_templates.append(template)

    # Merge env vars (later bundles override earlier ones)
    merged_env = {}
    for bundle in bundles:
        merged_env.update(bundle.env_vars)

    composed_name = "+".join(bundle_names)
    composed_description = f"Composed bundle: {', '.join(bundle_names)}"

    return SkillBundle(
        name=composed_name,
        description=composed_description,
        mcp_servers=list(servers_dict.values()),
        custom_agents=merged_agents,
        instruction_templates=merged_templates,
        env_vars=merged_env,
    )
