"""agent-context: Deterministic context injection for AI agent workspaces.

Usage:
    python -m agent_context inject /workspace [--task-id X] [--task-desc "..."]
"""

from .injector import inject, inject_custom_agents
from .profiles import (
    BUILTIN_PROFILES,
    AgentDefinition,
    MCPServer,
    ToolProfile,
    get_agent,
    get_profile,
)

__version__ = "0.1.0"
__all__ = [
    "inject",
    "inject_custom_agents",
    "BUILTIN_PROFILES",
    "AgentDefinition",
    "MCPServer",
    "ToolProfile",
    "get_profile",
    "get_agent",
]
