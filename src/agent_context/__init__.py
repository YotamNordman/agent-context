"""agent-context: Deterministic context injection for AI agent workspaces.

Usage:
    python -m agent_context inject /workspace [--task-id X] [--task-desc "..."] [--profile NAME]
"""

from .injector import inject
from .profiles import BUILTIN_PROFILES, MCPServer, ToolProfile, generate_mcp_config, get_profile

__version__ = "0.1.0"
__all__ = [
    "inject",
    "generate_mcp_config",
    "BUILTIN_PROFILES",
    "MCPServer",
    "ToolProfile",
    "get_profile",
]
