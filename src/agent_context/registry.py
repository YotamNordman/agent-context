"""Project profile registry — load project-specific tool configurations from YAML."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Optional

import yaml

from .profiles import BUILTIN_PROFILES, MCPServer, ToolProfile

# Path to the profiles.yaml file in the repo root
_DEFAULT_PROFILES_YAML = Path(__file__).parent.parent.parent / "profiles.yaml"


class ProfileRegistry:
    """Registry for mapping projects to their tool profiles."""

    def __init__(self, profiles_yaml_path: Optional[Path] = None):
        """Initialize the registry.
        
        Args:
            profiles_yaml_path: Path to profiles.yaml file. If None, uses default location.
        """
        self.profiles_yaml_path = profiles_yaml_path or _DEFAULT_PROFILES_YAML
        self._project_profiles: dict[str, dict | list] = {}
        self._loaded = False
        
    def _load_profiles_yaml(self) -> None:
        """Load project profile mappings from YAML file."""
        if self._loaded:
            return
            
        if not self.profiles_yaml_path.exists():
            self._project_profiles = {}
            self._loaded = True
            return
            
        with open(self.profiles_yaml_path, "r") as f:
            data = yaml.safe_load(f) or {}
            self._project_profiles = data.get("projects", {})
            self._loaded = True
    
    def get_profile(self, project_id: str) -> ToolProfile:
        """Get the tool profile for a project.
        
        Args:
            project_id: The project identifier
            
        Returns:
            ToolProfile for the project, or base profile if not configured
        """
        self._load_profiles_yaml()
        
        project_config = self._project_profiles.get(project_id)
        
        if project_config is None:
            # Fall back to base profile
            return self._get_base_profile()
        
        # Handle string profile name
        if isinstance(project_config, str):
            profile_name = project_config
            return self._get_profile_by_name(profile_name)
        
        # Handle dict with profile name and optional extensions
        if isinstance(project_config, dict):
            profile_name = project_config.get("profile", "base")
            extends = project_config.get("extends", [])
            
            # Get the base profile
            base_profile = self._get_profile_by_name(profile_name)
            
            # Add any additional MCP servers from the extends list
            if extends:
                base_profile = self._extend_profile(base_profile, extends)
            
            return base_profile
        
        # Fall back to base profile for invalid configs
        return self._get_base_profile()
    
    def _get_base_profile(self) -> ToolProfile:
        """Get a deep copy of the base profile."""
        return copy.deepcopy(BUILTIN_PROFILES.get("base") or ToolProfile(name="base"))
    
    def _get_profile_by_name(self, profile_name: str) -> ToolProfile:
        """Get a profile by name, with fallback to base.
        
        Args:
            profile_name: Name of the profile
            
        Returns:
            ToolProfile from BUILTIN_PROFILES, or base profile if not found
        """
        profile = BUILTIN_PROFILES.get(profile_name)
        if profile is None:
            return self._get_base_profile()
        return copy.deepcopy(profile)
    
    def _extend_profile(self, profile: ToolProfile, extends: list[str]) -> ToolProfile:
        """Extend a profile with additional MCP servers.
        
        Args:
            profile: The base profile to extend
            extends: List of MCP server names to add
            
        Returns:
            Extended profile with additional servers
        """
        # Collect all available MCP servers by their name
        from .profiles import _SERVERS
        
        # Create a set of existing server names to avoid duplicates
        existing_server_names = {server.name for server in profile.mcp_servers}
        
        # Add new servers
        for server_name in extends:
            if server_name in _SERVERS and server_name not in existing_server_names:
                profile.mcp_servers.append(copy.deepcopy(_SERVERS[server_name]))
        
        return profile


# Global registry instance
_registry: Optional[ProfileRegistry] = None


def _get_global_registry() -> ProfileRegistry:
    """Get or create the global registry instance."""
    global _registry
    if _registry is None:
        _registry = ProfileRegistry()
    return _registry


def get_profile(project_id: str) -> ToolProfile:
    """Get the tool profile for a project using the global registry.
    
    Args:
        project_id: The project identifier
        
    Returns:
        ToolProfile for the project
    """
    registry = _get_global_registry()
    return registry.get_profile(project_id)


def reset_registry() -> None:
    """Reset the global registry (useful for testing)."""
    global _registry
    _registry = None
