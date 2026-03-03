"""Load and manage tool profiles from profiles.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agent_context.profiles import ToolProfile, get_profile


class ProjectProfileRegistry:
    """Registry for mapping projects to tool profiles."""

    def __init__(self, registry_data: dict[str, Any]) -> None:
        """Initialize registry from parsed YAML data.

        Args:
            registry_data: Dictionary containing 'projects' key with project mappings.
        """
        self.projects = registry_data.get("projects", {})

    @classmethod
    def from_file(cls, filepath: str | Path) -> ProjectProfileRegistry:
        """Load project profile registry from a YAML file.

        Args:
            filepath: Path to profiles.yaml file.

        Returns:
            ProjectProfileRegistry instance.

        Raises:
            FileNotFoundError: If the file does not exist.
            yaml.YAMLError: If the file is not valid YAML.
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Profile registry file not found: {filepath}")

        with open(filepath) as f:
            data = yaml.safe_load(f) or {}

        return cls(data)

    def get_project_profile(self, project_name: str) -> ToolProfile | None:
        """Get the tool profile for a project.

        Args:
            project_name: Name of the project.

        Returns:
            ToolProfile instance if found, None otherwise.
        """
        if project_name not in self.projects:
            return None

        project_config = self.projects[project_name]
        if not isinstance(project_config, dict):
            return None

        profile_name = project_config.get("profile")
        if not profile_name:
            return None

        return get_profile(profile_name)

    def list_projects(self) -> list[str]:
        """List all registered projects.

        Returns:
            List of project names.
        """
        return list(self.projects.keys())

    def list_profiles_used(self) -> set[str]:
        """List all profiles used by registered projects.

        Returns:
            Set of profile names.
        """
        profiles = set()
        for project_config in self.projects.values():
            if isinstance(project_config, dict) and "profile" in project_config:
                profiles.add(project_config["profile"])
        return profiles
