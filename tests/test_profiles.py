"""Tests for tool profiles."""

from agent_context.profiles import (
    BUILTIN_PROFILES,
    AgentDefinition,
    MCPServer,
    ToolProfile,
    get_agent,
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
    """Tests that verify BUILTIN_PROFILES are protected from mutations via deep copying."""

    def test_env_var_mutations_dont_affect_builtin_profiles(self):
        """Test that modifying env_vars in a returned profile doesn't affect BUILTIN_PROFILES."""
        # Get a profile and modify its env_vars
        profile1 = get_profile("base")
        if profile1:
            profile1.env_vars["NEW_KEY"] = "new_value"

        # Get the same profile again - it should be unchanged
        profile2 = get_profile("base")
        assert profile2 is not None
        assert "NEW_KEY" not in profile2.env_vars, "Mutations should not persist due to deep copying"

    def test_mcp_servers_list_mutations_dont_affect_builtin_profiles(self):
        """Test that modifying mcp_servers list doesn't affect BUILTIN_PROFILES."""
        # Get a profile with servers and modify the list
        profile1 = get_profile("azure")  
        original_count = len(profile1.mcp_servers) if profile1 else 0

        if profile1:
            new_server = MCPServer(name="test", command="test-cmd")
            profile1.mcp_servers.append(new_server)

        # Get the same profile again - the original list should be unchanged
        profile2 = get_profile("azure")
        assert profile2 is not None
        assert len(profile2.mcp_servers) == original_count, "List mutations should not persist due to deep copying"
        
    def test_returned_profiles_are_independent_instances(self):
        """Test that multiple calls to get_profile return independent instances."""
        profile1 = get_profile("base")
        profile2 = get_profile("base")
        
        assert profile1 is not None
        assert profile2 is not None
        assert profile1 is not profile2, "Each call should return a separate deep copy"


class TestAgentDefinition:
    """Tests for AgentDefinition dataclass."""

    def test_create_agent_with_required_fields(self):
        """Test creating an AgentDefinition with only required fields."""
        agent = AgentDefinition(
            name="test-agent",
            description="Test agent",
            instructions="Do something",
        )
        assert agent.name == "test-agent"
        assert agent.description == "Test agent"
        assert agent.instructions == "Do something"
        assert agent.allowed_tools == []
        assert agent.mcp_servers == []

    def test_create_agent_with_all_fields(self):
        """Test creating an AgentDefinition with all fields."""
        agent = AgentDefinition(
            name="test-agent",
            description="Test agent",
            instructions="Do something",
            allowed_tools=["tool1", "tool2"],
            mcp_servers=["server1", "server2"],
        )
        assert agent.name == "test-agent"
        assert agent.description == "Test agent"
        assert agent.instructions == "Do something"
        assert agent.allowed_tools == ["tool1", "tool2"]
        assert agent.mcp_servers == ["server1", "server2"]

    def test_agent_fields_have_defaults(self):
        """Test that agent optional fields default to empty lists."""
        agent = AgentDefinition(
            name="test",
            description="test",
            instructions="test",
        )
        assert isinstance(agent.allowed_tools, list)
        assert isinstance(agent.mcp_servers, list)
        assert len(agent.allowed_tools) == 0
        assert len(agent.mcp_servers) == 0


class TestGetAgent:
    """Tests for get_agent function."""

    def test_get_predefined_incident_investigator_agent(self):
        """Test getting the incident-investigator agent."""
        agent = get_agent("incident-investigator")
        assert agent is not None
        assert agent.name == "incident-investigator"
        assert "incident" in agent.description.lower()
        assert len(agent.instructions) > 0
        assert "icm" in agent.mcp_servers

    def test_get_predefined_tsg_finder_agent(self):
        """Test getting the tsg-finder agent."""
        agent = get_agent("tsg-finder")
        assert agent is not None
        assert agent.name == "tsg-finder"
        assert "troubleshooting" in agent.description.lower()
        assert len(agent.instructions) > 0
        assert "msdocs" in agent.mcp_servers

    def test_get_nonexistent_agent(self):
        """Test getting a nonexistent agent returns None."""
        agent = get_agent("nonexistent-agent")
        assert agent is None

    def test_get_agent_returns_deep_copy(self):
        """Test that get_agent returns independent copies."""
        agent1 = get_agent("incident-investigator")
        agent2 = get_agent("incident-investigator")
        
        assert agent1 is not None
        assert agent2 is not None
        assert agent1 is not agent2, "Should return separate deep copies"
        
        # Verify mutation doesn't affect other copies
        if agent1:
            agent1.allowed_tools.append("new_tool")
            assert "new_tool" not in agent2.allowed_tools


class TestOncallProfileAgents:
    """Tests that verify oncall profile includes custom agents."""

    def test_oncall_profile_has_custom_agents(self):
        """Test that oncall profile includes custom agents."""
        profile = get_profile("oncall")
        assert profile is not None
        assert len(profile.custom_agents) > 0

    def test_oncall_profile_has_incident_investigator(self):
        """Test that oncall profile includes incident-investigator agent."""
        profile = get_profile("oncall")
        assert profile is not None
        assert "incident-investigator" in profile.custom_agents

    def test_oncall_profile_has_tsg_finder(self):
        """Test that oncall profile includes tsg-finder agent."""
        profile = get_profile("oncall")
        assert profile is not None
        assert "tsg-finder" in profile.custom_agents
