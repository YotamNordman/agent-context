"""agent-context: Deterministic context injection for AI agent workspaces.

Usage:
    python -m agent_context inject /workspace [--task-id X] [--task-desc "..."]
"""

from .injector import inject
from .profiles import BUILTIN_PROFILES, MCPServer, ToolProfile, get_profile
from .analyzer import analyze

__version__ = "0.1.0"
__all__ = ["inject", "BUILTIN_PROFILES", "MCPServer", "ToolProfile", "get_profile", "analyze"]
