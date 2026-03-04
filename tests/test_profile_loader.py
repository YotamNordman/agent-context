"""Tests for project profile registry and loading."""

import tempfile
from pathlib import Path

import pytest
import yaml

from agent_context.profile_loader import ProjectProfileRegistry
from agent_context.profiles import BUILTIN_PROFILES, get_profile


class TestProjectProfileRegistry:
    """Tests for ProjectProfileRegistry class."""

    def test_init_with_empty_data(self):
        """Test initializing registry with empty data."""
        registry = ProjectProfileRegistry({})
        assert registry.list_projects() == []

    def test_init_with_project_data(self):
        """Test initializing registry with project data."""
        data = {
            "projects": {
                "project1": {"profile": "base"},
                "project2": {"profile": "azure"},
            }
        }
        registry = ProjectProfileRegistry(data)
        assert set(registry.list_projects()) == {"project1", "project2"}

    def test_get_project_profile_found(self):
        """Test getting an existing project's profile."""
        data = {
            "projects": {
                "my-project": {"profile": "base"},
            }
        }
        registry = ProjectProfileRegistry(data)
        profile = registry.get_project_profile("my-project")
        assert profile is not None
        assert profile.name == "base"

    def test_get_project_profile_not_found(self):
        """Test getting a non-existent project returns None."""
        data = {"projects": {"project1": {"profile": "base"}}}
        registry = ProjectProfileRegistry(data)
        profile = registry.get_project_profile("nonexistent")
        assert profile is None

    def test_get_project_profile_invalid_format(self):
        """Test getting project with invalid format returns None."""
        data = {"projects": {"project1": "not-a-dict"}}
        registry = ProjectProfileRegistry(data)
        profile = registry.get_project_profile("project1")
        assert profile is None

    def test_get_project_profile_no_profile_field(self):
        """Test getting project without profile field returns None."""
        data = {"projects": {"project1": {"description": "No profile field"}}}
        registry = ProjectProfileRegistry(data)
        profile = registry.get_project_profile("project1")
        assert profile is None

    def test_get_project_profile_nonexistent_profile(self):
        """Test getting project with nonexistent profile returns None."""
        data = {"projects": {"project1": {"profile": "nonexistent-profile"}}}
        registry = ProjectProfileRegistry(data)
        profile = registry.get_project_profile("project1")
        assert profile is None

    def test_list_projects(self):
        """Test listing all registered projects."""
        data = {
            "projects": {
                "proj-a": {"profile": "base"},
                "proj-b": {"profile": "azure"},
                "proj-c": {"profile": "oncall"},
            }
        }
        registry = ProjectProfileRegistry(data)
        projects = registry.list_projects()
        assert set(projects) == {"proj-a", "proj-b", "proj-c"}

    def test_list_profiles_used(self):
        """Test listing all profiles used in the registry."""
        data = {
            "projects": {
                "proj1": {"profile": "base"},
                "proj2": {"profile": "azure"},
                "proj3": {"profile": "base"},
                "proj4": {"profile": "oncall"},
            }
        }
        registry = ProjectProfileRegistry(data)
        profiles = registry.list_profiles_used()
        assert profiles == {"base", "azure", "oncall"}

    def test_list_profiles_used_with_invalid_entries(self):
        """Test that invalid entries are skipped when listing profiles."""
        data = {
            "projects": {
                "proj1": {"profile": "base"},
                "proj2": "invalid",
                "proj3": {"description": "no profile"},
                "proj4": {"profile": "azure"},
            }
        }
        registry = ProjectProfileRegistry(data)
        profiles = registry.list_profiles_used()
        assert profiles == {"base", "azure"}

    def test_list_profiles_used_empty(self):
        """Test listing profiles when registry is empty."""
        registry = ProjectProfileRegistry({})
        profiles = registry.list_profiles_used()
        assert profiles == set()

    def test_profile_independence(self):
        """Test that returned profiles are independent instances."""
        data = {"projects": {"proj": {"profile": "base"}}}
        registry = ProjectProfileRegistry(data)
        
        profile1 = registry.get_project_profile("proj")
        profile2 = registry.get_project_profile("proj")
        
        assert profile1 is not None
        assert profile2 is not None
        # Should be different instances (due to deep copy in get_profile)
        assert profile1 is not profile2


class TestProjectProfileRegistryFileLoading:
    """Tests for loading profiles from YAML files."""

    def test_from_file_basic(self):
        """Test loading a basic YAML profile file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(
                {
                    "projects": {
                        "project1": {"profile": "base"},
                        "project2": {"profile": "azure"},
                    }
                },
                f,
            )
            temp_path = f.name

        try:
            registry = ProjectProfileRegistry.from_file(temp_path)
            assert set(registry.list_projects()) == {"project1", "project2"}
            assert registry.get_project_profile("project1").name == "base"
            assert registry.get_project_profile("project2").name == "azure"
        finally:
            Path(temp_path).unlink()

    def test_from_file_with_descriptions(self):
        """Test loading YAML file with descriptions."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(
                {
                    "projects": {
                        "my-project": {
                            "profile": "base",
                            "description": "A test project",
                        },
                    }
                },
                f,
            )
            temp_path = f.name

        try:
            registry = ProjectProfileRegistry.from_file(temp_path)
            assert registry.get_project_profile("my-project").name == "base"
        finally:
            Path(temp_path).unlink()

    def test_from_file_not_found(self):
        """Test that FileNotFoundError is raised when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            ProjectProfileRegistry.from_file("/nonexistent/path/profiles.yaml")

    def test_from_file_with_pathlib_path(self):
        """Test loading with a pathlib.Path object."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"projects": {"proj1": {"profile": "base"}}}, f)
            temp_path = Path(f.name)

        try:
            registry = ProjectProfileRegistry.from_file(temp_path)
            assert "proj1" in registry.list_projects()
        finally:
            temp_path.unlink()

    def test_from_file_empty_yaml(self):
        """Test loading an empty YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            registry = ProjectProfileRegistry.from_file(temp_path)
            assert registry.list_projects() == []
        finally:
            Path(temp_path).unlink()

    def test_from_file_no_projects_key(self):
        """Test loading YAML with no 'projects' key."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"other_key": {"data": "value"}}, f)
            temp_path = f.name

        try:
            registry = ProjectProfileRegistry.from_file(temp_path)
            assert registry.list_projects() == []
        finally:
            Path(temp_path).unlink()

    def test_from_file_invalid_yaml(self):
        """Test that yaml.YAMLError is raised for invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: syntax: here:")
            temp_path = f.name

        try:
            with pytest.raises(yaml.YAMLError):
                ProjectProfileRegistry.from_file(temp_path)
        finally:
            Path(temp_path).unlink()


class TestDefaultProfilesYaml:
    """Tests that verify the default profiles.yaml in the repo."""

    def test_load_default_profiles_yaml(self):
        """Test loading the default profiles.yaml from repo root."""
        repo_root = Path(__file__).parent.parent
        profiles_file = repo_root / "profiles.yaml"
        
        if not profiles_file.exists():
            pytest.skip("profiles.yaml not found in repo root")
        
        registry = ProjectProfileRegistry.from_file(profiles_file)
        
        # Verify all expected projects are present
        expected_projects = {
            "wow-hub",
            "wow-console", 
            "wow-infra",
            "agent-context",
            "agent-telemetry",
            "ezra",
            "datapipelines",
        }
        assert set(registry.list_projects()) == expected_projects

    def test_default_profiles_yaml_mappings(self):
        """Test that default profiles.yaml has correct profile mappings."""
        repo_root = Path(__file__).parent.parent
        profiles_file = repo_root / "profiles.yaml"
        
        if not profiles_file.exists():
            pytest.skip("profiles.yaml not found in repo root")
        
        registry = ProjectProfileRegistry.from_file(profiles_file)
        
        # Verify expected profile assignments
        assert registry.get_project_profile("wow-hub").name == "base"
        assert registry.get_project_profile("wow-console").name == "base"
        assert registry.get_project_profile("wow-infra").name == "base"
        assert registry.get_project_profile("agent-context").name == "base"
        assert registry.get_project_profile("agent-telemetry").name == "base"
        assert registry.get_project_profile("ezra").name == "oncall"
        assert registry.get_project_profile("datapipelines").name == "azure"

    def test_default_profiles_yaml_all_profiles_valid(self):
        """Test that all profiles in default profiles.yaml are valid."""
        repo_root = Path(__file__).parent.parent
        profiles_file = repo_root / "profiles.yaml"
        
        if not profiles_file.exists():
            pytest.skip("profiles.yaml not found in repo root")
        
        registry = ProjectProfileRegistry.from_file(profiles_file)
        
        # Verify all profiles are builtin profiles
        used_profiles = registry.list_profiles_used()
        for profile_name in used_profiles:
            assert profile_name in BUILTIN_PROFILES, f"Profile '{profile_name}' not in BUILTIN_PROFILES"
            profile = get_profile(profile_name)
            assert profile is not None, f"Profile '{profile_name}' could not be loaded"
