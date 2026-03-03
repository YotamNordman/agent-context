"""agent-context: Deterministic context injection for AI agent workspaces.

Usage:
    python -m agent_context inject /workspace [--task-id X] [--task-desc "..."]
"""

from .injector import inject

__version__ = "0.1.0"
__all__ = ["inject"]
