"""Tests for the injector — end-to-end: workspace → files written."""

import json
import os
import tempfile
from pathlib import Path

from agent_context.injector import inject, generate_mcp_config, _substitute_env_vars
from agent_context.profiles import MCPServer, ToolProfile


def _make_workspace(files: dict[str, str]) -> Path:
    tmp = Path(tempfile.mkdtemp())
    for path, content in files.items():
        p = tmp / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return tmp


class TestInjection:
    def test_injects_into_python_workspace(self):
        ws = _make_workspace({
            "pyproject.toml": '[project]\nname = "myapp"\n[tool.pytest.ini_options]\ntestpaths = ["tests"]',
            "src/myapp/__init__.py": "",
            "tests/test_main.py": "",
        })
        status = inject(ws)

        assert status["safety.instructions.md"] == "written"
        assert status["git-workflow.instructions.md"] == "written"
        assert status["testing.instructions.md"] == "written"
        assert status["copilot-instructions.md"] == "written"

        # Verify files exist
        assert (ws / ".github" / "instructions" / "safety.instructions.md").exists()
        assert (ws / ".github" / "copilot-instructions.md").exists()

    def test_injects_into_js_workspace(self):
        ws = _make_workspace({
            "package.json": json.dumps({
                "name": "myapp",
                "devDependencies": {"@playwright/test": "^1.58", "vite": "^6"},
                "scripts": {"build": "vite build", "test": "npx playwright test"},
            }),
            "tests/e2e.spec.js": "",
        })
        status = inject(ws)

        assert status["safety.instructions.md"] == "written"
        assert status["testing.instructions.md"] == "written"

        # Copilot instructions should mention playwright
        content = (ws / ".github" / "copilot-instructions.md").read_text()
        assert "playwright" in content.lower() or "npx" in content

    def test_skips_existing_files(self):
        ws = _make_workspace({
            "pyproject.toml": "",
            ".github/instructions/safety.instructions.md": "# Custom safety rules",
        })
        status = inject(ws)

        # Should skip the existing file
        assert status["safety.instructions.md"] == "skipped"
        # Existing content preserved
        content = (ws / ".github" / "instructions" / "safety.instructions.md").read_text()
        assert content == "# Custom safety rules"

    def test_overwrite_replaces_existing(self):
        ws = _make_workspace({
            "pyproject.toml": "",
            ".github/instructions/safety.instructions.md": "# Old",
        })
        status = inject(ws, overwrite=True)

        assert status["safety.instructions.md"] == "written"
        content = (ws / ".github" / "instructions" / "safety.instructions.md").read_text()
        assert "Banned Files" in content

    def test_task_context_injected(self):
        ws = _make_workspace({"pyproject.toml": ""})
        inject(ws, task_context={
            "task_id": "fix-auth",
            "acceptance_criteria": "Login returns 200",
            "feedback": "Missing error handling for invalid tokens",
        })

        content = (ws / ".github" / "copilot-instructions.md").read_text()
        assert "Login returns 200" in content
        assert "Missing error handling" in content

    def test_minimal_workspace(self):
        ws = _make_workspace({"README.md": "# Hello"})
        status = inject(ws)

        # Should still inject safety + git workflow + copilot-instructions
        assert status["safety.instructions.md"] == "written"
        assert status["git-workflow.instructions.md"] == "written"
        assert status["copilot-instructions.md"] == "written"
        # No testing template (no test runner detected)
        assert "testing.instructions.md" not in status

    def test_raises_on_missing_workspace(self):
        import pytest
        with pytest.raises(ValueError):
            inject("/nonexistent/path")

    def test_creates_github_directory(self):
        ws = _make_workspace({"main.py": "print('hello')"})
        inject(ws)
        assert (ws / ".github" / "instructions").is_dir()


class TestMCPConfigGeneration:
    """Tests for MCP config generation."""

    def test_generate_mcp_config_empty_profile(self):
        """Test generating config with empty profile (no servers)."""
        ws = _make_workspace({"README.md": "# Hello"})
        profile = ToolProfile(name="empty", mcp_servers=[])

        status = generate_mcp_config(ws, profile)

        assert status["mcp-config.json"] == "written"
        config_file = ws / ".copilot" / "mcp-config.json"
        assert config_file.exists()

        config = json.loads(config_file.read_text())
        assert "mcpServers" in config
        assert config["mcpServers"] == {}

    def test_generate_mcp_config_with_servers(self):
        """Test generating config with multiple servers."""
        ws = _make_workspace({"README.md": "# Hello"})

        servers = [
            MCPServer(name="server1", command="cmd1", args=["arg1", "arg2"]),
            MCPServer(name="server2", command="cmd2", args=[], env={"KEY": "value"}),
        ]
        profile = ToolProfile(name="test", mcp_servers=servers)

        status = generate_mcp_config(ws, profile)

        assert status["mcp-config.json"] == "written"
        config_file = ws / ".copilot" / "mcp-config.json"
        config = json.loads(config_file.read_text())

        assert len(config["mcpServers"]) == 2
        assert "server1" in config["mcpServers"]
        assert "server2" in config["mcpServers"]

        # Check server1 config
        s1 = config["mcpServers"]["server1"]
        assert s1["type"] == "stdio"
        assert s1["command"] == "cmd1"
        assert s1["args"] == ["arg1", "arg2"]

        # Check server2 config
        s2 = config["mcpServers"]["server2"]
        assert s2["type"] == "stdio"
        assert s2["command"] == "cmd2"
        assert s2["env"] == {"KEY": "value"}
        assert "args" not in s2 or s2.get("args") == []

    def test_generate_mcp_config_creates_copilot_dir(self):
        """Test that .copilot directory is created if it doesn't exist."""
        ws = _make_workspace({"README.md": "# Hello"})
        assert not (ws / ".copilot").exists()

        profile = ToolProfile(name="test", mcp_servers=[])
        generate_mcp_config(ws, profile)

        assert (ws / ".copilot").is_dir()

    def test_generate_mcp_config_env_substitution(self):
        """Test environment variable substitution in command and args."""
        ws = _make_workspace({"README.md": "# Hello"})

        # Set test env var
        os.environ["TEST_API_KEY"] = "secret123"

        servers = [
            MCPServer(
                name="server1",
                command="mcp-server",
                args=["--token=${TEST_API_KEY}"],
                env={"API_KEY": "$TEST_API_KEY"},
            ),
        ]
        profile = ToolProfile(name="test", mcp_servers=servers)

        status = generate_mcp_config(ws, profile)
        assert status["mcp-config.json"] == "written"

        config = json.loads((ws / ".copilot" / "mcp-config.json").read_text())
        server_config = config["mcpServers"]["server1"]

        assert server_config["args"][0] == "--token=secret123"
        assert server_config["env"]["API_KEY"] == "secret123"

        # Cleanup
        del os.environ["TEST_API_KEY"]

    def test_generate_mcp_config_env_overrides(self):
        """Test that env_overrides take precedence."""
        ws = _make_workspace({"README.md": "# Hello"})

        servers = [
            MCPServer(
                name="server1",
                command="mcp-server",
                args=["--token=${TOKEN}"],
                env={"TOKEN": "default"},
            ),
        ]
        profile = ToolProfile(name="test", mcp_servers=servers)

        overrides = {"TOKEN": "override_value"}
        generate_mcp_config(ws, profile, env_overrides=overrides)

        config = json.loads((ws / ".copilot" / "mcp-config.json").read_text())
        server_config = config["mcpServers"]["server1"]

        assert server_config["args"][0] == "--token=override_value"
        assert server_config["env"]["TOKEN"] == "override_value"

    def test_generate_mcp_config_missing_env_var(self):
        """Test that missing env vars are left as-is."""
        ws = _make_workspace({"README.md": "# Hello"})

        servers = [
            MCPServer(
                name="server1",
                command="mcp-server",
                args=["--token=${MISSING_VAR}"],
            ),
        ]
        profile = ToolProfile(name="test", mcp_servers=servers)

        generate_mcp_config(ws, profile)
        config = json.loads((ws / ".copilot" / "mcp-config.json").read_text())
        server_config = config["mcpServers"]["server1"]

        # Missing vars should remain unchanged
        assert server_config["args"][0] == "--token=${MISSING_VAR}"

    def test_generate_mcp_config_raises_on_missing_workspace(self):
        """Test that missing workspace raises ValueError."""
        import pytest
        profile = ToolProfile(name="test", mcp_servers=[])
        with pytest.raises(ValueError):
            generate_mcp_config("/nonexistent/path", profile)

    def test_generate_mcp_config_json_format(self):
        """Test that generated JSON is properly formatted."""
        ws = _make_workspace({"README.md": "# Hello"})
        servers = [MCPServer(name="test", command="test-cmd")]
        profile = ToolProfile(name="test", mcp_servers=servers)

        generate_mcp_config(ws, profile)

        config_file = ws / ".copilot" / "mcp-config.json"
        content = config_file.read_text()

        # Should be valid JSON
        config = json.loads(content)
        assert "mcpServers" in config

        # Should be formatted with indentation
        assert "  " in content  # Check for indentation

    def test_generate_mcp_config_multiple_calls(self):
        """Test that multiple calls overwrite the config file."""
        ws = _make_workspace({"README.md": "# Hello"})

        servers1 = [MCPServer(name="server1", command="cmd1")]
        profile1 = ToolProfile(name="profile1", mcp_servers=servers1)
        generate_mcp_config(ws, profile1)

        config1 = json.loads((ws / ".copilot" / "mcp-config.json").read_text())
        assert len(config1["mcpServers"]) == 1
        assert "server1" in config1["mcpServers"]

        # Call again with different profile
        servers2 = [
            MCPServer(name="server2", command="cmd2"),
            MCPServer(name="server3", command="cmd3"),
        ]
        profile2 = ToolProfile(name="profile2", mcp_servers=servers2)
        generate_mcp_config(ws, profile2)

        config2 = json.loads((ws / ".copilot" / "mcp-config.json").read_text())
        assert len(config2["mcpServers"]) == 2
        assert "server2" in config2["mcpServers"]
        assert "server3" in config2["mcpServers"]
        assert "server1" not in config2["mcpServers"]


class TestEnvVarSubstitution:
    """Tests for environment variable substitution."""

    def test_substitute_env_vars_brace_syntax(self):
        """Test ${VAR} syntax substitution."""
        os.environ["TEST_VAR"] = "test_value"

        result = _substitute_env_vars("prefix-${TEST_VAR}-suffix")
        assert result == "prefix-test_value-suffix"

        del os.environ["TEST_VAR"]

    def test_substitute_env_vars_simple_syntax(self):
        """Test $VAR syntax substitution."""
        os.environ["TEST_VAR"] = "test_value"

        result = _substitute_env_vars("prefix-$TEST_VAR-suffix")
        assert result == "prefix-test_value-suffix"

        del os.environ["TEST_VAR"]

    def test_substitute_env_vars_multiple(self):
        """Test multiple variable substitution."""
        os.environ["VAR1"] = "value1"
        os.environ["VAR2"] = "value2"

        result = _substitute_env_vars("${VAR1}-$VAR2-${VAR1}")
        assert result == "value1-value2-value1"

        del os.environ["VAR1"]
        del os.environ["VAR2"]

    def test_substitute_env_vars_missing_var(self):
        """Test that missing variables are left as-is."""
        result = _substitute_env_vars("prefix-${MISSING_VAR}-suffix")
        assert result == "prefix-${MISSING_VAR}-suffix"

    def test_substitute_env_vars_overrides_precedence(self):
        """Test that overrides take precedence over environment."""
        os.environ["TEST_VAR"] = "env_value"

        result = _substitute_env_vars(
            "value=${TEST_VAR}",
            overrides={"TEST_VAR": "override_value"},
        )
        assert result == "value=override_value"

        del os.environ["TEST_VAR"]

    def test_substitute_env_vars_empty_string(self):
        """Test substitution on empty string."""
        result = _substitute_env_vars("")
        assert result == ""

    def test_substitute_env_vars_no_vars(self):
        """Test substitution on string with no variables."""
        result = _substitute_env_vars("hello-world")
        assert result == "hello-world"

    def test_substitute_env_vars_complex_names(self):
        """Test substitution with underscores and numbers in var names."""
        os.environ["VAR_NAME_123"] = "complex_value"

        result = _substitute_env_vars("${VAR_NAME_123}")
        assert result == "complex_value"

        del os.environ["VAR_NAME_123"]
