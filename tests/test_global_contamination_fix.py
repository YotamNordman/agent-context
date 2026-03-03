"""Test to verify the critical global contamination fix."""

from agent_context.skills import get_bundle, list_bundle_names


class TestGlobalContaminationFix:
    """Tests that verify global state contamination is fixed."""
    
    def test_no_global_state_contamination(self):
        """Test that bundles are properly isolated from global contamination."""
        # Get two separate instances of the same bundle
        bundle1 = get_bundle("testing")
        bundle2 = get_bundle("testing") 
        
        # They should be different instances
        assert bundle1 is not bundle2
        
        # Mutate the first bundle
        bundle1.env_vars["HACKED"] = "yes"
        
        # Second bundle should be unaffected
        assert "HACKED" not in bundle2.env_vars
        
        # Getting a fresh copy should also be unaffected
        bundle3 = get_bundle("testing")
        assert "HACKED" not in bundle3.env_vars
    
    def test_no_cross_bundle_server_contamination(self):
        """Test that bundles don't share server objects that can be contaminated."""
        oncall_bundle = get_bundle("oncall")
        azure_bundle = get_bundle("azure-dev")
        
        # Both bundles have adx server, but they should be separate objects
        oncall_adx = None
        azure_adx = None
        
        for server in oncall_bundle.mcp_servers:
            if server.name == "adx":
                oncall_adx = server
                break
        
        for server in azure_bundle.mcp_servers:
            if server.name == "adx":
                azure_adx = server
                break
        
        assert oncall_adx is not None
        assert azure_adx is not None
        assert oncall_adx is not azure_adx  # Different objects
        
        # Contaminate oncall's adx server
        oncall_adx.env["POISON"] = "evil"
        
        # Azure's adx server should be unaffected
        assert "POISON" not in azure_adx.env
        
        # Fresh copies should also be unaffected
        fresh_azure = get_bundle("azure-dev")
        for server in fresh_azure.mcp_servers:
            if server.name == "adx":
                assert "POISON" not in server.env
                break

    def test_list_bundle_names_works(self):
        """Test that list_bundle_names function works correctly."""
        names = list_bundle_names()
        
        assert isinstance(names, list)
        assert "oncall" in names
        assert "azure-dev" in names 
        assert "web-dev" in names
        assert "testing" in names
        assert len(names) == 4