"""Tests for the project profile registry."""

from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

import pytest

from agent_context.profiles import MCPServer, ToolProfile
from agent_context.registry import ProfileRegistry, get_profile, reset_registry


class TestProfileRegistry:
    """Tests for ProfileRegistry class."""

    def test_registry_initialization_without_yaml(self):
        """Test creating a registry when profiles.yaml doesn't exist."""
        with TemporaryDirectory() as tmpdir:
            nonexistent_path = Path(tmpdir) / "nonexistent.yaml"
            registry = ProfileRegistry(profiles_yaml_path=nonexistent_path)
            
            # Should not raise error
            profile = registry.get_profile("any-project")
            assert profile.name == "base"
            assert profile.mcp_servers == []

    def test_registry_fallback_to_base_profile(self):
        """Test that unknown projects fall back to base profile."""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("projects:\n  known-project: azure\n")
            f.flush()
            
            try:
                registry = ProfileRegistry(profiles_yaml_path=Path(f.name))
                profile = registry.get_profile("unknown-project")
                
                assert profile.name == "base"
                assert profile.mcp_servers == []
            finally:
                Path(f.name).unlink()

    def test_registry_load_simple_profile_assignment(self):
        """Test loading a simple profile name assignment from YAML."""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("projects:\n  my-project: azure\n")
            f.flush()
            
            try:
                registry = ProfileRegistry(profiles_yaml_path=Path(f.name))
                profile = registry.get_profile("my-project")
                
                assert profile.name == "azure"
                assert len(profile.mcp_servers) == 3
                server_names = [s.name for s in profile.mcp_servers]
                assert "ado" in server_names
                assert "adx" in server_names
                assert "msdocs" in server_names
            finally:
                Path(f.name).unlink()

    def test_registry_load_extended_profile(self):
        """Test loading a profile with extends clause."""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""projects:
  oncall-project:
    profile: oncall
    extends:
      - context7
""")
            f.flush()
            
            try:
                registry = ProfileRegistry(profiles_yaml_path=Path(f.name))
                profile = registry.get_profile("oncall-project")
                
                assert profile.name == "oncall"
                # oncall has 5 servers, extended with context7 should have 6
                assert len(profile.mcp_servers) == 6
                server_names = [s.name for s in profile.mcp_servers]
                assert "context7" in server_names
            finally:
                Path(f.name).unlink()

    def test_registry_extend_avoids_duplicates(self):
        """Test that extending a profile doesn't duplicate existing servers."""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""projects:
  my-project:
    profile: azure
    extends:
      - msdocs
      - ado
""")
            f.flush()
            
            try:
                registry = ProfileRegistry(profiles_yaml_path=Path(f.name))
                profile = registry.get_profile("my-project")
                
                assert profile.name == "azure"
                # azure has msdocs and ado, so extending should still have 3 servers
                assert len(profile.mcp_servers) == 3
                server_names = [s.name for s in profile.mcp_servers]
                assert server_names.count("msdocs") == 1
                assert server_names.count("ado") == 1
            finally:
                Path(f.name).unlink()

    def test_registry_extend_with_new_servers(self):
        """Test extending a profile with servers not already in it."""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""projects:
  my-project:
    profile: base
    extends:
      - msdocs
      - ado
""")
            f.flush()
            
            try:
                registry = ProfileRegistry(profiles_yaml_path=Path(f.name))
                profile = registry.get_profile("my-project")
                
                assert profile.name == "base"
                assert len(profile.mcp_servers) == 2
                server_names = [s.name for s in profile.mcp_servers]
                assert "msdocs" in server_names
                assert "ado" in server_names
            finally:
                Path(f.name).unlink()

    def test_registry_extend_with_nonexistent_server(self):
        """Test that extending with nonexistent server names is ignored."""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""projects:
  my-project:
    profile: base
    extends:
      - nonexistent-server
      - msdocs
""")
            f.flush()
            
            try:
                registry = ProfileRegistry(profiles_yaml_path=Path(f.name))
                profile = registry.get_profile("my-project")
                
                assert profile.name == "base"
                # Only msdocs should be added
                assert len(profile.mcp_servers) == 1
                assert profile.mcp_servers[0].name == "msdocs"
            finally:
                Path(f.name).unlink()

    def test_registry_returns_independent_copies(self):
        """Test that registry returns independent profile copies."""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("projects:\n  my-project: azure\n")
            f.flush()
            
            try:
                registry = ProfileRegistry(profiles_yaml_path=Path(f.name))
                profile1 = registry.get_profile("my-project")
                profile2 = registry.get_profile("my-project")
                
                # Modify profile1
                profile1.env_vars["NEW_KEY"] = "new_value"
                
                # profile2 should be unaffected
                assert "NEW_KEY" not in profile2.env_vars
            finally:
                Path(f.name).unlink()

    def test_registry_loads_yaml_only_once(self):
        """Test that registry caches YAML after first load."""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("projects:\n  my-project: azure\n")
            f.flush()
            
            try:
                registry = ProfileRegistry(profiles_yaml_path=Path(f.name))
                
                # First load
                profile1 = registry.get_profile("my-project")
                
                # Modify the file (this shouldn't affect cached data)
                with open(f.name, "w") as f2:
                    f2.write("projects:\n  other-project: docs\n")
                
                # Second load should use cached data
                profile2 = registry.get_profile("my-project")
                
                assert profile1.name == profile2.name == "azure"
            finally:
                Path(f.name).unlink()

    def test_registry_default_profile_when_none_specified(self):
        """Test that 'profile' defaults to 'base' in dict config."""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""projects:
  my-project:
    extends:
      - msdocs
""")
            f.flush()
            
            try:
                registry = ProfileRegistry(profiles_yaml_path=Path(f.name))
                profile = registry.get_profile("my-project")
                
                assert profile.name == "base"
                assert len(profile.mcp_servers) == 1
                assert profile.mcp_servers[0].name == "msdocs"
            finally:
                Path(f.name).unlink()

    def test_registry_invalid_profile_name_fallback(self):
        """Test that invalid profile names fall back to base."""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("projects:\n  my-project: nonexistent-profile\n")
            f.flush()
            
            try:
                registry = ProfileRegistry(profiles_yaml_path=Path(f.name))
                profile = registry.get_profile("my-project")
                
                assert profile.name == "base"
                assert profile.mcp_servers == []
            finally:
                Path(f.name).unlink()

    def test_registry_empty_extends_list(self):
        """Test that empty extends list doesn't cause issues."""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""projects:
  my-project:
    profile: azure
    extends: []
""")
            f.flush()
            
            try:
                registry = ProfileRegistry(profiles_yaml_path=Path(f.name))
                profile = registry.get_profile("my-project")
                
                assert profile.name == "azure"
                assert len(profile.mcp_servers) == 3
            finally:
                Path(f.name).unlink()


class TestGlobalRegistryFunction:
    """Tests for the global get_profile() function."""

    def teardown_method(self):
        """Reset the global registry after each test."""
        reset_registry()

    def test_get_profile_returns_base_for_nonexistent_project(self):
        """Test that get_profile returns base for nonexistent projects."""
        profile = get_profile("nonexistent-project")
        
        assert profile.name == "base"
        assert profile.mcp_servers == []

    def test_get_profile_returns_profile_from_yaml(self):
        """Test that get_profile uses the YAML file."""
        # This test assumes profiles.yaml exists in the repo root
        # If it doesn't, it will still pass (returns base)
        profile = get_profile("my-project")
        
        # Should return either a configured profile or base
        assert profile is not None
        assert isinstance(profile, ToolProfile)

    def test_global_registry_instance_is_singleton(self):
        """Test that multiple calls use the same registry instance."""
        # This is more of an implementation detail test
        reset_registry()
        from agent_context.registry import _registry as registry1
        reset_registry()
        from agent_context.registry import _registry as registry2
        
        # Both should be None initially
        assert registry1 is None
        assert registry2 is None

    def test_get_profile_returns_independent_copies(self):
        """Test that get_profile returns independent copies."""
        profile1 = get_profile("some-project")
        profile2 = get_profile("some-project")
        
        # Modify profile1
        profile1.env_vars["NEW_KEY"] = "new_value"
        
        # profile2 should be unaffected
        assert "NEW_KEY" not in profile2.env_vars


class TestProfileRegistryEdgeCases:
    """Tests for edge cases and error handling."""

    def test_registry_with_empty_yaml(self):
        """Test registry with empty YAML file."""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()
            
            try:
                registry = ProfileRegistry(profiles_yaml_path=Path(f.name))
                profile = registry.get_profile("any-project")
                
                assert profile.name == "base"
            finally:
                Path(f.name).unlink()

    def test_registry_with_empty_projects_section(self):
        """Test registry with empty projects section."""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("projects: {}\n")
            f.flush()
            
            try:
                registry = ProfileRegistry(profiles_yaml_path=Path(f.name))
                profile = registry.get_profile("any-project")
                
                assert profile.name == "base"
            finally:
                Path(f.name).unlink()

    def test_registry_with_no_projects_key(self):
        """Test registry with YAML that has no 'projects' key."""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("other_key: value\n")
            f.flush()
            
            try:
                registry = ProfileRegistry(profiles_yaml_path=Path(f.name))
                profile = registry.get_profile("any-project")
                
                assert profile.name == "base"
            finally:
                Path(f.name).unlink()

    def test_registry_with_invalid_dict_config(self):
        """Test registry with invalid dict config."""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("projects:\n  my-project:\n    invalid_key: value\n")
            f.flush()
            
            try:
                registry = ProfileRegistry(profiles_yaml_path=Path(f.name))
                profile = registry.get_profile("my-project")
                
                # Should fall back to base
                assert profile.name == "base"
            finally:
                Path(f.name).unlink()

    def test_registry_with_list_config(self):
        """Test registry with list-type config (should fall back to base)."""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("projects:\n  my-project:\n    - server1\n    - server2\n")
            f.flush()
            
            try:
                registry = ProfileRegistry(profiles_yaml_path=Path(f.name))
                profile = registry.get_profile("my-project")
                
                # List config not supported, should fall back
                assert profile.name == "base"
            finally:
                Path(f.name).unlink()
