"""Tests for CLI profile support and MCP config generation."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from agent_context import generate_mcp_config, get_profile, inject
from agent_context.profiles import MCPServer, ToolProfile


class TestGenerateMCPConfig:
    """Tests for generate_mcp_config function."""

    def test_generate_mcp_config_with_none_profile(self):
        """Test generate_mcp_config with None profile."""
        config = generate_mcp_config(profile=None)
        assert config["mcp_servers"] == []
        assert config["custom_agents"] == []
        assert config["env_vars"] == {}
        assert "project_id" not in config or config.get("project_id") is None

    def test_generate_mcp_config_with_profile_and_project_id(self):
        """Test generate_mcp_config with both profile and project_id."""
        profile = get_profile("azure")
        config = generate_mcp_config(profile=profile, project_id="test-proj-123")
        
        assert config["profile_name"] == "azure"
        assert config["project_id"] == "test-proj-123"
        assert len(config["mcp_servers"]) == 3
        assert config["custom_agents"] == []
        assert isinstance(config["env_vars"], dict)

    def test_generate_mcp_config_mcp_servers_structure(self):
        """Test that MCP servers in config have correct structure."""
        profile = ToolProfile(
            name="test",
            mcp_servers=[
                MCPServer(
                    name="test-server",
                    command="test-cmd",
                    args=["--arg1"],
                    env={"KEY": "value"},
                    tools_filter=["tool1"],
                )
            ],
        )
        config = generate_mcp_config(profile=profile)
        
        assert len(config["mcp_servers"]) == 1
        server = config["mcp_servers"][0]
        assert server["name"] == "test-server"
        assert server["command"] == "test-cmd"
        assert server["args"] == ["--arg1"]
        assert server["env"] == {"KEY": "value"}
        assert server["tools_filter"] == ["tool1"]

    def test_generate_mcp_config_with_custom_agents(self):
        """Test that custom agents are preserved in config."""
        profile = ToolProfile(
            name="test",
            custom_agents=["agent1", "agent2"],
        )
        config = generate_mcp_config(profile=profile)
        
        assert config["custom_agents"] == ["agent1", "agent2"]

    def test_generate_mcp_config_with_env_vars(self):
        """Test that environment variables are preserved in config."""
        profile = ToolProfile(
            name="test",
            env_vars={"VAR1": "value1", "VAR2": "value2"},
        )
        config = generate_mcp_config(profile=profile)
        
        assert config["env_vars"] == {"VAR1": "value1", "VAR2": "value2"}

    def test_generate_mcp_config_returns_dict(self):
        """Test that generate_mcp_config returns a dict."""
        config = generate_mcp_config()
        assert isinstance(config, dict)


class TestInjectWithProfile:
    """Tests for inject function with profile parameter."""

    def test_inject_with_profile_creates_mcp_config(self):
        """Test that inject creates mcp-config.json when profile is provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # Create minimal Python project structure
            (workspace / "pyproject.toml").write_text(
                '[project]\nname="test"\nversion="0.1.0"\n'
            )
            
            profile = get_profile("base")
            status = inject(workspace, profile=profile, overwrite=True)
            
            # Check that mcp-config.json was created
            assert "mcp-config.json" in status
            assert status["mcp-config.json"] == "written"
            
            # Verify the file exists and is valid JSON
            mcp_config_path = workspace / ".github" / "mcp-config.json"
            assert mcp_config_path.exists()
            config = json.loads(mcp_config_path.read_text())
            assert config["profile_name"] == "base"

    def test_inject_without_profile_skips_mcp_config(self):
        """Test that inject does not create mcp-config.json without profile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            (workspace / "pyproject.toml").write_text(
                '[project]\nname="test"\nversion="0.1.0"\n'
            )
            
            status = inject(workspace, overwrite=True)
            
            # Check that mcp-config.json was not created
            assert "mcp-config.json" not in status
            mcp_config_path = workspace / ".github" / "mcp-config.json"
            assert not mcp_config_path.exists()

    def test_inject_respects_profile_data(self):
        """Test that inject uses profile data in mcp-config.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            (workspace / "pyproject.toml").write_text(
                '[project]\nname="test"\nversion="0.1.0"\n'
            )
            
            profile = get_profile("oncall")
            inject(workspace, profile=profile, overwrite=True)
            
            mcp_config_path = workspace / ".github" / "mcp-config.json"
            config = json.loads(mcp_config_path.read_text())
            
            # oncall profile should have 5 MCP servers
            assert len(config["mcp_servers"]) == 5
            server_names = [s["name"] for s in config["mcp_servers"]]
            assert "icm" in server_names


class TestCLIWithProfile:
    """Tests for CLI with --profile argument."""

    def test_cli_accepts_profile_argument(self):
        """Test that CLI accepts --profile argument."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            (workspace / "pyproject.toml").write_text(
                '[project]\nname="test"\nversion="0.1.0"\n'
            )
            
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "agent_context",
                    "inject",
                    str(workspace),
                    "--profile",
                    "base",
                ],
                capture_output=True,
                text=True,
            )
            
            assert result.returncode == 0
            output = json.loads(result.stdout)
            assert "mcp-config.json" in output
            assert output["mcp-config.json"] == "written"

    def test_cli_with_invalid_profile_exits_with_error(self):
        """Test that CLI exits with error for invalid profile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            (workspace / "pyproject.toml").write_text(
                '[project]\nname="test"\nversion="0.1.0"\n'
            )
            
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "agent_context",
                    "inject",
                    str(workspace),
                    "--profile",
                    "nonexistent",
                ],
                capture_output=True,
                text=True,
            )
            
            assert result.returncode == 1
            assert "Profile not found" in result.stderr

    def test_cli_with_profile_and_other_options(self):
        """Test CLI with profile and other options like task-id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            (workspace / "pyproject.toml").write_text(
                '[project]\nname="test"\nversion="0.1.0"\n'
            )
            
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "agent_context",
                    "inject",
                    str(workspace),
                    "--profile",
                    "azure",
                    "--task-id",
                    "task-123",
                ],
                capture_output=True,
                text=True,
            )
            
            assert result.returncode == 0
            output = json.loads(result.stdout)
            assert "mcp-config.json" in output

    def test_cli_with_all_profiles(self):
        """Test CLI works with all builtin profiles."""
        for profile_name in ["base", "oncall", "azure", "docs"]:
            with tempfile.TemporaryDirectory() as tmpdir:
                workspace = Path(tmpdir)
                
                (workspace / "pyproject.toml").write_text(
                    '[project]\nname="test"\nversion="0.1.0"\n'
                )
                
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "agent_context",
                        "inject",
                        str(workspace),
                        "--profile",
                        profile_name,
                    ],
                    capture_output=True,
                    text=True,
                )
                
                assert result.returncode == 0, f"Failed for profile: {profile_name}"
                output = json.loads(result.stdout)
                assert "mcp-config.json" in output


class TestAPIExports:
    """Tests for API exports in __init__.py."""

    def test_generate_mcp_config_exported(self):
        """Test that generate_mcp_config is exported from agent_context."""
        from agent_context import generate_mcp_config as exported_func
        
        assert callable(exported_func)
        config = exported_func()
        assert isinstance(config, dict)

    def test_profile_functions_exported(self):
        """Test that profile functions are exported."""
        from agent_context import get_profile, BUILTIN_PROFILES
        
        assert callable(get_profile)
        assert isinstance(BUILTIN_PROFILES, dict)
        assert len(BUILTIN_PROFILES) > 0
