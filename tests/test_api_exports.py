"""Tests for public API exports."""

def test_skill_bundle_api_exports():
    """Test that SkillBundle API is properly exported."""
    import agent_context
    
    # Test that all skill bundle functions are available at top level
    assert hasattr(agent_context, 'SkillBundle')
    assert hasattr(agent_context, 'get_bundle')
    assert hasattr(agent_context, 'compose_bundles')
    assert hasattr(agent_context, 'list_bundle_names')
    
    # Test that they work
    bundle = agent_context.get_bundle('oncall')
    assert bundle is not None
    assert bundle.name == 'oncall'
    
    # Test compose functionality
    composed = agent_context.compose_bundles('oncall', 'testing')
    assert composed.name == 'oncall+testing'
    
    # Test list functionality
    names = agent_context.list_bundle_names()
    assert 'oncall' in names
    assert 'azure-dev' in names
    assert 'web-dev' in names
    assert 'testing' in names
    
    # Test SkillBundle creation
    bundle_class = agent_context.SkillBundle
    custom_bundle = bundle_class(name="test", description="Test bundle")
    assert custom_bundle.name == "test"