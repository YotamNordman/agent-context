"""agent-context: Deterministic context injection for AI agent workspaces.

Usage:
    python -m agent_context inject /workspace [--task-id X] [--task-desc "..."]
"""

from .injector import inject
from .profiles import BUILTIN_PROFILES, MCPServer, ToolProfile, get_profile
from .skills import SkillBundle, compose_bundles, get_bundle, list_bundle_names

__version__ = "0.2.0"
__all__ = [
    "inject",
    "BUILTIN_PROFILES",
    "MCPServer", 
    "ToolProfile",
    "get_profile",
    "SkillBundle",
    "compose_bundles",
    "get_bundle", 
    "list_bundle_names",
]
