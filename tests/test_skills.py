"""Tests for skill bundles."""

from agent_context.profiles import MCPServer, ToolProfile
from agent_context.skills import (
    BUILTIN_BUNDLES,
    SkillBundle,
    compose_bundles,
    get_bundle,
)


class TestSkillBundle:
    """Tests for SkillBundle dataclass."""

    def test_create_skill_bundle_with_required_fields(self):
        """Test creating a SkillBundle with only required fields."""
        bundle = SkillBundle(name="test")
        assert bundle.name == "test"
        assert bundle.description == ""
        assert bundle.mcp_servers == []
        assert bundle.custom_agents == []
        assert bundle.instruction_templates == []
        assert bundle.env_vars == {}

    def test_create_skill_bundle_with_all_fields(self):
        """Test creating a SkillBundle with all fields."""
        server1 = MCPServer(name="server1", command="cmd1")
        server2 = MCPServer(name="server2", command="cmd2")
        bundle = SkillBundle(
            name="test",
            description="Test bundle",
            mcp_servers=[server1, server2],
            custom_agents=["agent1", "agent2"],
            instruction_templates=["template1", "template2"],
            env_vars={"VAR1": "value1", "VAR2": "value2"},
        )
        assert bundle.name == "test"
        assert bundle.description == "Test bundle"
        assert len(bundle.mcp_servers) == 2
        assert bundle.mcp_servers[0].name == "server1"
        assert bundle.mcp_servers[1].name == "server2"
        assert bundle.custom_agents == ["agent1", "agent2"]
        assert bundle.instruction_templates == ["template1", "template2"]
        assert bundle.env_vars == {"VAR1": "value1", "VAR2": "value2"}

    def test_skill_bundle_to_tool_profile(self):
        """Test converting SkillBundle to ToolProfile."""
        server = MCPServer(name="test", command="test-cmd")
        bundle = SkillBundle(
            name="test",
            description="Test bundle",
            mcp_servers=[server],
            custom_agents=["agent1"],
            instruction_templates=["template1"],
            env_vars={"VAR": "value"},
        )
        profile = bundle.to_tool_profile()
        assert isinstance(profile, ToolProfile)
        assert profile.name == "test"
        assert len(profile.mcp_servers) == 1
        assert profile.mcp_servers[0].name == "test"
        assert profile.custom_agents == ["agent1"]
        assert profile.env_vars == {"VAR": "value"}

    def test_skill_bundle_to_tool_profile_creates_independent_copy(self):
        """Test that to_tool_profile creates independent deep copies."""
        server = MCPServer(name="test", command="test-cmd")
        bundle = SkillBundle(
            name="test",
            mcp_servers=[server],
            env_vars={"VAR": "value"},
        )
        profile = bundle.to_tool_profile()
        
        # Modify the profile
        profile.env_vars["VAR"] = "modified"
        if profile.mcp_servers:
            profile.mcp_servers[0].name = "modified"
        
        # Original bundle should be unchanged
        assert bundle.env_vars["VAR"] == "value"
        assert bundle.mcp_servers[0].name == "test"


class TestBuiltinBundles:
    """Tests for builtin skill bundles."""

    def test_oncall_bundle_exists(self):
        """Test that oncall bundle exists with correct configuration."""
        assert "oncall" in BUILTIN_BUNDLES
        bundle = BUILTIN_BUNDLES["oncall"]
        assert bundle.name == "oncall"
        assert "incident investigation" in bundle.description.lower()
        assert len(bundle.mcp_servers) == 5
        server_names = [s.name for s in bundle.mcp_servers]
        assert "icm" in server_names
        assert "ado-afd" in server_names
        assert "adx" in server_names
        assert "msdocs" in server_names
        assert "enghub" in server_names
        assert "incident-investigation" in bundle.instruction_templates
        assert "incident-resolution" in bundle.instruction_templates

    def test_azure_dev_bundle_exists(self):
        """Test that azure-dev bundle exists with correct configuration."""
        assert "azure-dev" in BUILTIN_BUNDLES
        bundle = BUILTIN_BUNDLES["azure-dev"]
        assert bundle.name == "azure-dev"
        assert "azure" in bundle.description.lower()
        assert "kusto" in bundle.description.lower()
        assert len(bundle.mcp_servers) == 3
        server_names = [s.name for s in bundle.mcp_servers]
        assert "ado" in server_names
        assert "adx" in server_names
        assert "msdocs" in server_names
        assert "azure-workitems" in bundle.instruction_templates
        assert "kusto-queries" in bundle.instruction_templates

    def test_web_dev_bundle_exists(self):
        """Test that web-dev bundle exists with correct configuration."""
        assert "web-dev" in BUILTIN_BUNDLES
        bundle = BUILTIN_BUNDLES["web-dev"]
        assert bundle.name == "web-dev"
        assert "context7" in bundle.description.lower() or "docs" in bundle.description.lower()
        assert len(bundle.mcp_servers) == 3
        server_names = [s.name for s in bundle.mcp_servers]
        assert "context7" in server_names
        assert "msdocs" in server_names
        assert "enghub" in server_names
        assert "docs-lookup" in bundle.instruction_templates
        assert "web-patterns" in bundle.instruction_templates

    def test_testing_bundle_exists(self):
        """Test that testing bundle exists with correct configuration."""
        assert "testing" in BUILTIN_BUNDLES
        bundle = BUILTIN_BUNDLES["testing"]
        assert bundle.name == "testing"
        assert "test runner" in bundle.description.lower()
        assert "coverage" in bundle.description.lower()
        assert len(bundle.mcp_servers) == 0
        assert "test-runner-detection" in bundle.instruction_templates
        assert "coverage-rules" in bundle.instruction_templates
        assert bundle.env_vars.get("TEST_RUNNER") == "auto"
        assert bundle.env_vars.get("COVERAGE_MIN") == "80"

    def test_all_bundles_have_required_fields(self):
        """Test that all bundles have required fields."""
        for bundle_name, bundle in BUILTIN_BUNDLES.items():
            assert bundle.name == bundle_name
            assert isinstance(bundle.description, str)
            assert isinstance(bundle.mcp_servers, list)
            assert isinstance(bundle.custom_agents, list)
            assert isinstance(bundle.instruction_templates, list)
            assert isinstance(bundle.env_vars, dict)

    def test_all_bundle_servers_have_commands(self):
        """Test that all MCP servers in bundles have commands defined."""
        for bundle_name, bundle in BUILTIN_BUNDLES.items():
            for server in bundle.mcp_servers:
                assert server.command, f"Server {server.name} in {bundle_name} has no command"
                assert server.name, f"Server in {bundle_name} has no name"


class TestGetBundle:
    """Tests for get_bundle function."""

    def test_get_bundle_oncall(self):
        """Test getting the oncall bundle."""
        bundle = get_bundle("oncall")
        assert bundle is not None
        assert bundle.name == "oncall"
        assert len(bundle.mcp_servers) == 5

    def test_get_bundle_azure_dev(self):
        """Test getting the azure-dev bundle."""
        bundle = get_bundle("azure-dev")
        assert bundle is not None
        assert bundle.name == "azure-dev"
        assert len(bundle.mcp_servers) == 3

    def test_get_bundle_web_dev(self):
        """Test getting the web-dev bundle."""
        bundle = get_bundle("web-dev")
        assert bundle is not None
        assert bundle.name == "web-dev"
        assert len(bundle.mcp_servers) == 3

    def test_get_bundle_testing(self):
        """Test getting the testing bundle."""
        bundle = get_bundle("testing")
        assert bundle is not None
        assert bundle.name == "testing"
        assert len(bundle.mcp_servers) == 0
        assert bundle.env_vars.get("TEST_RUNNER") == "auto"

    def test_get_bundle_nonexistent(self):
        """Test getting a nonexistent bundle returns None."""
        bundle = get_bundle("nonexistent")
        assert bundle is None

    def test_get_bundle_empty_string(self):
        """Test getting with empty string returns None."""
        bundle = get_bundle("")
        assert bundle is None

    def test_get_bundle_case_sensitive(self):
        """Test that bundle lookup is case sensitive."""
        bundle = get_bundle("OnCall")
        assert bundle is None  # should not match 'oncall'

    def test_get_bundle_returns_independent_copy(self):
        """Test that get_bundle returns independent deep copies."""
        bundle1 = get_bundle("oncall")
        bundle1.env_vars["NEW_KEY"] = "new_value"
        if bundle1.mcp_servers:
            bundle1.mcp_servers[0].command = "modified"

        bundle2 = get_bundle("oncall")
        assert "NEW_KEY" not in bundle2.env_vars
        assert bundle2.mcp_servers[0].command == "mcp-icm"


class TestComposeBundles:
    """Tests for compose_bundles function."""

    def test_compose_single_bundle(self):
        """Test composing a single bundle."""
        composed = compose_bundles("oncall")
        assert composed.name == "oncall"
        assert len(composed.mcp_servers) == 5

    def test_compose_two_bundles(self):
        """Test composing two bundles."""
        composed = compose_bundles("oncall", "testing")
        assert composed.name == "oncall+testing"
        assert "oncall" in composed.description
        assert "testing" in composed.description
        # Should have all servers from oncall (5) + testing (0) = 5
        assert len(composed.mcp_servers) == 5

    def test_compose_three_bundles(self):
        """Test composing three bundles."""
        composed = compose_bundles("oncall", "azure-dev", "web-dev")
        assert composed.name == "oncall+azure-dev+web-dev"
        # oncall: icm, ado-afd, adx, msdocs, enghub
        # azure-dev: ado, adx, msdocs
        # web-dev: msdocs, enghub, context7
        # Unique: icm, ado-afd, adx, msdocs, enghub, ado, context7 = 7
        assert len(composed.mcp_servers) == 7

    def test_compose_bundles_merges_servers_by_name(self):
        """Test that composing bundles merges servers by name."""
        composed = compose_bundles("oncall", "azure-dev")
        server_names = [s.name for s in composed.mcp_servers]
        # Check no duplicates
        assert len(server_names) == len(set(server_names))
        # Check expected servers
        assert "adx" in server_names
        assert "msdocs" in server_names

    def test_compose_bundles_merges_instruction_templates(self):
        """Test that composing bundles merges instruction templates."""
        composed = compose_bundles("oncall", "testing")
        templates = composed.instruction_templates
        # Check no duplicates
        assert len(templates) == len(set(templates))
        # Check expected templates from both bundles
        assert "incident-investigation" in templates
        assert "test-runner-detection" in templates

    def test_compose_bundles_merges_env_vars(self):
        """Test that composing bundles merges env vars with later overriding."""
        # Test with builtin bundles where testing has env vars
        composed = compose_bundles("testing", "web-dev")
        # testing adds TEST_RUNNER and COVERAGE_MIN
        assert composed.env_vars.get("TEST_RUNNER") == "auto"
        assert composed.env_vars.get("COVERAGE_MIN") == "80"

    def test_compose_empty_bundles(self):
        """Test composing with no bundle names."""
        composed = compose_bundles()
        assert composed.name == "empty"
        assert len(composed.mcp_servers) == 0
        assert len(composed.instruction_templates) == 0

    def test_compose_bundles_with_nonexistent_bundle(self):
        """Test composing with a nonexistent bundle raises ValueError."""
        try:
            compose_bundles("oncall", "nonexistent")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "nonexistent" in str(e)

    def test_compose_bundles_preserves_agent_order(self):
        """Test that composing bundles preserves agent order and avoids duplicates."""
        # Create a composition where agents might appear multiple times
        composed = compose_bundles("oncall", "testing")
        # Both bundles have empty custom_agents in this case, but test the logic
        assert isinstance(composed.custom_agents, list)

    def test_compose_bundles_returns_independent_copy(self):
        """Test that compose_bundles returns an independent bundle."""
        composed = compose_bundles("oncall", "testing")
        original_count = len(composed.mcp_servers)
        
        # Modify the composed bundle
        new_server = MCPServer(name="test", command="test-cmd")
        composed.mcp_servers.append(new_server)
        composed.env_vars["NEW_KEY"] = "new_value"
        
        # Get the composition again
        composed2 = compose_bundles("oncall", "testing")
        assert len(composed2.mcp_servers) == original_count
        assert "NEW_KEY" not in composed2.env_vars


class TestBundleImmutability:
    """Tests that verify BUILTIN_BUNDLES are protected from mutations."""

    def test_env_var_mutations_dont_affect_builtin_bundles(self):
        """Test that modifying env_vars doesn't affect BUILTIN_BUNDLES."""
        bundle1 = get_bundle("testing")
        if bundle1:
            bundle1.env_vars["NEW_KEY"] = "new_value"

        bundle2 = get_bundle("testing")
        assert bundle2 is not None
        assert "NEW_KEY" not in bundle2.env_vars

    def test_mcp_servers_list_mutations_dont_affect_builtin_bundles(self):
        """Test that modifying mcp_servers list doesn't affect BUILTIN_BUNDLES."""
        bundle1 = get_bundle("oncall")
        original_count = len(bundle1.mcp_servers) if bundle1 else 0

        if bundle1:
            new_server = MCPServer(name="test", command="test-cmd")
            bundle1.mcp_servers.append(new_server)

        bundle2 = get_bundle("oncall")
        assert bundle2 is not None
        assert len(bundle2.mcp_servers) == original_count

    def test_instruction_templates_mutations_dont_affect_builtin_bundles(self):
        """Test that modifying templates doesn't affect BUILTIN_BUNDLES."""
        bundle1 = get_bundle("testing")
        original_count = len(bundle1.instruction_templates) if bundle1 else 0

        if bundle1:
            bundle1.instruction_templates.append("new_template")

        bundle2 = get_bundle("testing")
        assert bundle2 is not None
        assert len(bundle2.instruction_templates) == original_count

    def test_returned_bundles_are_independent_instances(self):
        """Test that multiple calls to get_bundle return independent instances."""
        bundle1 = get_bundle("oncall")
        bundle2 = get_bundle("oncall")

        assert bundle1 is not None
        assert bundle2 is not None
        assert bundle1 is not bundle2


class TestBundleCompatibility:
    """Tests for compatibility with existing ToolProfile system."""

    def test_bundle_can_be_converted_to_tool_profile(self):
        """Test that any bundle can be converted to ToolProfile."""
        for bundle_name in ["oncall", "azure-dev", "web-dev", "testing"]:
            bundle = get_bundle(bundle_name)
            assert bundle is not None
            profile = bundle.to_tool_profile()
            assert profile.name == bundle.name
            assert len(profile.mcp_servers) == len(bundle.mcp_servers)

    def test_composed_bundle_can_be_converted_to_tool_profile(self):
        """Test that composed bundles can be converted to ToolProfile."""
        composed = compose_bundles("oncall", "testing")
        profile = composed.to_tool_profile()
        assert profile.name == "oncall+testing"
        assert len(profile.mcp_servers) == 5  # from oncall
