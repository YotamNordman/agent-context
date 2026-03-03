"""Tests for tool profiles."""

from agent_context.profiles import (
    BUILTIN_PROFILES,
    MCPServer,
    ToolProfile,
    get_profile,
)


class TestMCPServer:
    """Tests for MCPServer dataclass."""

    def test_create_mcp_server_with_required_fields(self):
        """Test creating an MCPServer with only required fields."""
        server = MCPServer(name="test", command="test-cmd")
        assert server.name == "test"
        assert server.command == "test-cmd"
        assert server.args == []
        assert server.env == {}
        assert server.tools_filter is None

    def test_create_mcp_server_with_all_fields(self):
        """Test creating an MCPServer with all fields."""
        server = MCPServer(
            name="test",
            command="test-cmd",
            args=["--arg1", "--arg2"],
            env={"KEY": "value"},
            tools_filter=["tool1", "tool2"],
        )
        assert server.name == "test"
        assert server.command == "test-cmd"
        assert server.args == ["--arg1", "--arg2"]
        assert server.env == {"KEY": "value"}
        assert server.tools_filter == ["tool1", "tool2"]

    def test_mcp_server_tools_filter_optional(self):
        """Test that tools_filter is optional and defaults to None."""
        server = MCPServer(name="test", command="test-cmd")
        assert server.tools_filter is None


class TestToolProfile:
    """Tests for ToolProfile dataclass."""

    def test_create_tool_profile_with_required_fields(self):
        """Test creating a ToolProfile with only required fields."""
        profile = ToolProfile(name="test")
        assert profile.name == "test"
        assert profile.mcp_servers == []
        assert profile.custom_agents == []
        assert profile.env_vars == {}

    def test_create_tool_profile_with_all_fields(self):
        """Test creating a ToolProfile with all fields."""
        server1 = MCPServer(name="server1", command="cmd1")
        server2 = MCPServer(name="server2", command="cmd2")
        profile = ToolProfile(
            name="test",
            mcp_servers=[server1, server2],
            custom_agents=["agent1", "agent2"],
            env_vars={"VAR1": "value1", "VAR2": "value2"},
        )
        assert profile.name == "test"
        assert len(profile.mcp_servers) == 2
        assert profile.mcp_servers[0].name == "server1"
        assert profile.mcp_servers[1].name == "server2"
        assert profile.custom_agents == ["agent1", "agent2"]
        assert profile.env_vars == {"VAR1": "value1", "VAR2": "value2"}


class TestBuiltinProfiles:
    """Tests for builtin profiles."""

    def test_base_profile_exists(self):
        """Test that base profile exists and has no MCP servers."""
        assert "base" in BUILTIN_PROFILES
        profile = BUILTIN_PROFILES["base"]
        assert profile.name == "base"
        assert profile.mcp_servers == []
        assert profile.custom_agents == []
        assert profile.env_vars == {}

    def test_oncall_profile_exists(self):
        """Test that oncall profile exists with correct servers."""
        assert "oncall" in BUILTIN_PROFILES
        profile = BUILTIN_PROFILES["oncall"]
        assert profile.name == "oncall"
        assert len(profile.mcp_servers) == 5
        server_names = [s.name for s in profile.mcp_servers]
        assert "icm" in server_names
        assert "ado-afd" in server_names
        assert "adx" in server_names
        assert "msdocs" in server_names
        assert "enghub" in server_names

    def test_azure_profile_exists(self):
        """Test that azure profile exists with correct servers."""
        assert "azure" in BUILTIN_PROFILES
        profile = BUILTIN_PROFILES["azure"]
        assert profile.name == "azure"
        assert len(profile.mcp_servers) == 3
        server_names = [s.name for s in profile.mcp_servers]
        assert "ado" in server_names
        assert "adx" in server_names
        assert "msdocs" in server_names

    def test_docs_profile_exists(self):
        """Test that docs profile exists with correct servers."""
        assert "docs" in BUILTIN_PROFILES
        profile = BUILTIN_PROFILES["docs"]
        assert profile.name == "docs"
        assert len(profile.mcp_servers) == 3
        server_names = [s.name for s in profile.mcp_servers]
        assert "msdocs" in server_names
        assert "enghub" in server_names
        assert "context7" in server_names

    def test_all_mcp_servers_have_command(self):
        """Test that all MCP servers in profiles have commands defined."""
        for profile_name, profile in BUILTIN_PROFILES.items():
            for server in profile.mcp_servers:
                assert server.command, f"Server {server.name} in {profile_name} has no command"
                assert server.name, f"Server in {profile_name} has no name"

    def test_profile_servers_have_default_values(self):
        """Test that profile servers have default values for optional fields."""
        for profile_name, profile in BUILTIN_PROFILES.items():
            for server in profile.mcp_servers:
                assert isinstance(server.args, list)
                assert isinstance(server.env, dict)


class TestGetProfile:
    """Tests for get_profile function."""

    def test_get_profile_base(self):
        """Test getting the base profile."""
        profile = get_profile("base")
        assert profile is not None
        assert profile.name == "base"

    def test_get_profile_oncall(self):
        """Test getting the oncall profile."""
        profile = get_profile("oncall")
        assert profile is not None
        assert profile.name == "oncall"

    def test_get_profile_azure(self):
        """Test getting the azure profile."""
        profile = get_profile("azure")
        assert profile is not None
        assert profile.name == "azure"

    def test_get_profile_docs(self):
        """Test getting the docs profile."""
        profile = get_profile("docs")
        assert profile is not None
        assert profile.name == "docs"

    def test_get_profile_nonexistent(self):
        """Test getting a nonexistent profile returns None."""
        profile = get_profile("nonexistent")
        assert profile is None

    def test_get_profile_empty_string(self):
        """Test getting with empty string returns None."""
        profile = get_profile("")
        assert profile is None

    def test_get_profile_case_sensitive(self):
        """Test that profile lookup is case sensitive."""
        profile = get_profile("Base")
        assert profile is None  # should not match 'base'


class TestProfileImmutability:
    """Tests for profile data integrity."""

    def test_modifying_returned_profile_doesnt_affect_builtin(self):
        """Test that modifying a returned profile doesn't affect the builtin."""
        profile1 = get_profile("base")
        if profile1:
            # Attempt to modify the returned profile
            profile1.env_vars["NEW_KEY"] = "new_value"

        # Get the profile again and verify it's unchanged
        profile2 = get_profile("base")
        # With deep copying, modifications should NOT persist
        assert profile2 is not None
        assert "NEW_KEY" not in profile2.env_vars  # Should be isolated due to deep copying

    def test_modifying_servers_list_doesnt_affect_builtin(self):
        """Test that modifying server list doesn't affect the builtin."""
        profile1 = get_profile("azure")  # Use a profile with servers
        original_count = len(profile1.mcp_servers) if profile1 else 0

        if profile1:
            # Add a new server to the returned profile
            new_server = MCPServer(name="test", command="test-cmd")
            profile1.mcp_servers.append(new_server)

        # Get the profile again and verify the original list is unchanged
        profile2 = get_profile("azure")
        assert profile2 is not None
        assert len(profile2.mcp_servers) == original_count  # Should be unchanged due to deep copying
        
    def test_returned_profiles_are_independent_instances(self):
        """Test that multiple calls return independent instances."""
        profile1 = get_profile("base")
        profile2 = get_profile("base")
        
        assert profile1 is not None
        assert profile2 is not None
        assert profile1 is not profile2  # Should be different instances
