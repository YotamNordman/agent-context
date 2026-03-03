"""agent-context: Deterministic context injection for AI agent workspaces.

Usage:
    python -m agent_context inject /workspace [--task-id X] [--task-desc "..."]
"""

from .injector import inject
from .manifest import generate_manifest, manifest_to_dict, manifest_to_json, ManifestData
from .profiles import BUILTIN_PROFILES, MCPServer, ToolProfile, get_profile

__version__ = "0.1.0"
__all__ = [
    "inject",
    "generate_manifest",
    "manifest_to_dict",
    "manifest_to_json",
    "ManifestData",
    "BUILTIN_PROFILES",
    "MCPServer",
    "ToolProfile",
    "get_profile",
]
