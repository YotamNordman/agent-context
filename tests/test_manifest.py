"""Tests for the manifest generator — outputs JSON describing agent configuration."""

import json
import tempfile
from pathlib import Path

import pytest

from agent_context.manifest import (
    ManifestData,
    generate_manifest,
    manifest_to_dict,
    manifest_to_json,
)
from agent_context.profiles import MCPServer, ToolProfile


def _make_workspace(files: dict[str, str]) -> Path:
    """Helper to create a temporary workspace with files."""
    tmp = Path(tempfile.mkdtemp())
    for path, content in files.items():
        p = tmp / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return tmp


class TestGenerateManifest:
    """Tests for generate_manifest function."""

    def test_generates_manifest_with_base_profile(self):
        """Test generating manifest with default base profile."""
        ws = _make_workspace({"pyproject.toml": '[project]\nname = "test"'})
        manifest = generate_manifest(ws)

        assert isinstance(manifest, ManifestData)
        assert manifest.workspace == str(ws)
        assert manifest.profile_name == "base"
        assert manifest.mcp_servers == []
        assert manifest.custom_agents == []
        assert manifest.env_vars == {}
        assert manifest.estimated_context_tokens > 0

    def test_generates_manifest_with_named_profile(self):
        """Test generating manifest with a named profile."""
        ws = _make_workspace({"pyproject.toml": ""})
        manifest = generate_manifest(ws, profile="azure")

        assert manifest.profile_name == "azure"
        assert len(manifest.mcp_servers) == 3
        server_names = [s["name"] for s in manifest.mcp_servers]
        assert "ado" in server_names
        assert "adx" in server_names
        assert "msdocs" in server_names

    def test_generates_manifest_with_profile_object(self):
        """Test generating manifest with a ToolProfile object."""
        ws = _make_workspace({"pyproject.toml": ""})
        server = MCPServer(name="custom", command="custom-cmd")
        profile = ToolProfile(
            name="custom-profile",
            mcp_servers=[server],
            custom_agents=["agent1"],
            env_vars={"CUSTOM_VAR": "value"},
        )

        manifest = generate_manifest(ws, profile=profile)

        assert manifest.profile_name == "custom-profile"
        assert len(manifest.mcp_servers) == 1
        assert manifest.mcp_servers[0]["name"] == "custom"
        assert manifest.mcp_servers[0]["command"] == "custom-cmd"
        assert manifest.custom_agents == ["agent1"]
        assert manifest.env_vars == {"CUSTOM_VAR": "value"}

    def test_generates_manifest_with_task_context(self):
        """Test generating manifest with task context."""
        ws = _make_workspace({"pyproject.toml": ""})
        task_context = {
            "task_id": "fix-auth",
            "description": "Fix authentication bug",
            "acceptance_criteria": "Login returns 200",
            "feedback": "Missing error handling",
        }

        manifest = generate_manifest(ws, task_context=task_context)

        assert manifest.task_context == task_context

    def test_generated_manifest_includes_instructions(self):
        """Test that manifest includes rendered instructions."""
        ws = _make_workspace({
            "pyproject.toml": '[project]\nname = "test"\n[tool.pytest.ini_options]'
        })
        manifest = generate_manifest(ws)

        assert "safety.instructions.md" in manifest.instructions
        assert "git-workflow.instructions.md" in manifest.instructions
        assert "copilot-instructions.md" in manifest.instructions
        # Should have testing instructions since pyproject.toml is present
        assert "testing.instructions.md" in manifest.instructions

    def test_generated_manifest_includes_workspace_info(self):
        """Test that manifest includes workspace analysis."""
        ws = _make_workspace({
            "pyproject.toml": '[project]\nname = "test"',
            "src/app.py": "",
        })
        manifest = generate_manifest(ws)

        assert "workspace_info" in manifest.__dict__
        assert "languages" in manifest.workspace_info
        assert "python" in manifest.workspace_info["languages"]
        assert manifest.workspace_info["path"] == str(ws)

    def test_raises_on_nonexistent_workspace(self):
        """Test that ValueError is raised for nonexistent workspace."""
        with pytest.raises(ValueError, match="Workspace not found"):
            generate_manifest("/nonexistent/path")

    def test_raises_on_invalid_profile_name(self):
        """Test that ValueError is raised for unknown profile."""
        ws = _make_workspace({"README.md": ""})
        with pytest.raises(ValueError, match="Unknown profile"):
            generate_manifest(ws, profile="nonexistent-profile")

    def test_raises_on_invalid_profile_type(self):
        """Test that ValueError is raised for invalid profile type."""
        ws = _make_workspace({"README.md": ""})
        with pytest.raises(ValueError, match="Invalid profile type"):
            generate_manifest(ws, profile=12345)

    def test_estimated_context_tokens_greater_than_zero(self):
        """Test that estimated context tokens is always positive."""
        ws = _make_workspace({})
        manifest = generate_manifest(ws)
        assert manifest.estimated_context_tokens > 0

    def test_estimated_context_tokens_increases_with_instructions(self):
        """Test that more instructions increase estimated tokens."""
        ws1 = _make_workspace({"README.md": "# Empty workspace"})
        manifest1 = generate_manifest(ws1)

        ws2 = _make_workspace({
            "pyproject.toml": '[project]\nname = "test"\n[tool.pytest.ini_options]\ntestpaths = ["tests"]',
            "src/main.py": "",
            "tests/test_main.py": "",
        })
        manifest2 = generate_manifest(ws2)

        # More complete workspace should estimate more tokens
        assert manifest2.estimated_context_tokens > manifest1.estimated_context_tokens

    def test_mcp_servers_preserve_all_fields(self):
        """Test that MCP server fields are preserved in manifest."""
        ws = _make_workspace({})
        server = MCPServer(
            name="test-server",
            command="test-cmd",
            args=["--flag1", "--flag2"],
            env={"ENV_VAR": "value"},
            tools_filter=["tool1", "tool2"],
        )
        profile = ToolProfile(name="test", mcp_servers=[server])

        manifest = generate_manifest(ws, profile=profile)

        assert len(manifest.mcp_servers) == 1
        srv = manifest.mcp_servers[0]
        assert srv["name"] == "test-server"
        assert srv["command"] == "test-cmd"
        assert srv["args"] == ["--flag1", "--flag2"]
        assert srv["env"] == {"ENV_VAR": "value"}
        assert srv["tools_filter"] == ["tool1", "tool2"]

    def test_manifest_with_python_and_js_workspace(self):
        """Test manifest generation for workspace with both Python and JS."""
        ws = _make_workspace({
            "pyproject.toml": '[project]\nname = "test"',
            "package.json": json.dumps({
                "name": "myapp",
                "scripts": {"test": "npm test"},
            }),
            "src/main.py": "",
        })
        manifest = generate_manifest(ws)

        assert "python" in manifest.workspace_info["languages"]
        assert "javascript" in manifest.workspace_info["languages"]

    def test_oncall_profile_in_manifest(self):
        """Test manifest with oncall profile includes all servers."""
        ws = _make_workspace({})
        manifest = generate_manifest(ws, profile="oncall")

        assert manifest.profile_name == "oncall"
        assert len(manifest.mcp_servers) == 5
        server_names = [s["name"] for s in manifest.mcp_servers]
        assert "icm" in server_names
        assert "ado-afd" in server_names
        assert "adx" in server_names
        assert "msdocs" in server_names
        assert "enghub" in server_names

    def test_docs_profile_in_manifest(self):
        """Test manifest with docs profile."""
        ws = _make_workspace({})
        manifest = generate_manifest(ws, profile="docs")

        assert manifest.profile_name == "docs"
        assert len(manifest.mcp_servers) == 3
        server_names = [s["name"] for s in manifest.mcp_servers]
        assert "msdocs" in server_names
        assert "enghub" in server_names
        assert "context7" in server_names


class TestManifestToDict:
    """Tests for manifest_to_dict function."""

    def test_converts_manifest_to_dict(self):
        """Test that manifest_to_dict returns a dict."""
        ws = _make_workspace({})
        manifest = generate_manifest(ws)
        manifest_dict = manifest_to_dict(manifest)

        assert isinstance(manifest_dict, dict)
        assert "workspace" in manifest_dict
        assert "profile_name" in manifest_dict
        assert "instructions" in manifest_dict
        assert "mcp_servers" in manifest_dict
        assert "custom_agents" in manifest_dict
        assert "env_vars" in manifest_dict
        assert "workspace_info" in manifest_dict
        assert "estimated_context_tokens" in manifest_dict

    def test_dict_values_match_manifest(self):
        """Test that dict values match manifest attributes."""
        ws = _make_workspace({})
        manifest = generate_manifest(ws, profile="azure")
        manifest_dict = manifest_to_dict(manifest)

        assert manifest_dict["workspace"] == manifest.workspace
        assert manifest_dict["profile_name"] == manifest.profile_name
        assert manifest_dict["mcp_servers"] == manifest.mcp_servers
        assert manifest_dict["custom_agents"] == manifest.custom_agents
        assert manifest_dict["env_vars"] == manifest.env_vars
        assert manifest_dict["estimated_context_tokens"] == manifest.estimated_context_tokens

    def test_dict_is_json_serializable(self):
        """Test that the dict is JSON serializable."""
        ws = _make_workspace({})
        manifest = generate_manifest(ws)
        manifest_dict = manifest_to_dict(manifest)

        # Should not raise
        json_str = json.dumps(manifest_dict)
        assert isinstance(json_str, str)


class TestManifestToJson:
    """Tests for manifest_to_json function."""

    def test_converts_manifest_to_json_string(self):
        """Test that manifest_to_json returns a string."""
        ws = _make_workspace({})
        manifest = generate_manifest(ws)
        json_str = manifest_to_json(manifest)

        assert isinstance(json_str, str)
        # Should be valid JSON
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_json_has_all_required_fields(self):
        """Test that JSON contains all manifest fields."""
        ws = _make_workspace({})
        manifest = generate_manifest(ws, profile="azure")
        json_str = manifest_to_json(manifest)
        parsed = json.loads(json_str)

        assert "workspace" in parsed
        assert "profile_name" in parsed
        assert "task_context" in parsed
        assert "instructions" in parsed
        assert "mcp_servers" in parsed
        assert "custom_agents" in parsed
        assert "env_vars" in parsed
        assert "workspace_info" in parsed
        assert "estimated_context_tokens" in parsed

    def test_json_output_indented_by_default(self):
        """Test that JSON output is indented by default."""
        ws = _make_workspace({})
        manifest = generate_manifest(ws)
        json_str = manifest_to_json(manifest)

        # Indented JSON should have newlines
        assert "\n" in json_str

    def test_json_output_compact_with_none_indent(self):
        """Test that JSON output is compact with indent=None."""
        ws = _make_workspace({})
        manifest = generate_manifest(ws)
        json_str = manifest_to_json(manifest, indent=None)

        # Compact JSON should have no newlines (except maybe at the end)
        assert json_str.count("\n") <= 1

    def test_json_output_with_task_context(self):
        """Test that JSON includes task context."""
        ws = _make_workspace({})
        task_context = {
            "task_id": "test-task",
            "description": "A test task",
        }
        manifest = generate_manifest(ws, task_context=task_context)
        json_str = manifest_to_json(manifest)
        parsed = json.loads(json_str)

        assert parsed["task_context"] == task_context

    def test_json_mcp_servers_complete(self):
        """Test that JSON contains complete MCP server info."""
        ws = _make_workspace({})
        server = MCPServer(
            name="test",
            command="test-cmd",
            args=["--arg"],
            env={"KEY": "val"},
            tools_filter=["tool"],
        )
        profile = ToolProfile(name="test", mcp_servers=[server])

        manifest = generate_manifest(ws, profile=profile)
        json_str = manifest_to_json(manifest)
        parsed = json.loads(json_str)

        assert len(parsed["mcp_servers"]) == 1
        srv = parsed["mcp_servers"][0]
        assert srv["name"] == "test"
        assert srv["command"] == "test-cmd"
        assert srv["args"] == ["--arg"]
        assert srv["env"] == {"KEY": "val"}
        assert srv["tools_filter"] == ["tool"]

    def test_json_round_trip(self):
        """Test that JSON can be parsed and used to reconstruct data."""
        ws = _make_workspace({
            "pyproject.toml": '[project]\nname = "test"'
        })
        manifest = generate_manifest(ws, profile="azure", task_context={"id": "task1"})
        json_str = manifest_to_json(manifest)
        parsed = json.loads(json_str)

        assert parsed["workspace"] == str(ws)
        assert parsed["profile_name"] == "azure"
        assert len(parsed["mcp_servers"]) == 3
        assert parsed["task_context"]["id"] == "task1"
        assert isinstance(parsed["estimated_context_tokens"], int)


class TestManifestDataStructure:
    """Tests for ManifestData dataclass."""

    def test_manifest_data_creation(self):
        """Test creating ManifestData directly."""
        data = ManifestData(
            workspace="/path/to/ws",
            profile_name="test",
            task_context={"id": "1"},
            instructions={"file": "content"},
            mcp_servers=[],
            custom_agents=["agent1"],
            env_vars={"VAR": "val"},
            workspace_info={"languages": ["python"]},
            estimated_context_tokens=500,
        )

        assert data.workspace == "/path/to/ws"
        assert data.profile_name == "test"
        assert data.task_context == {"id": "1"}
        assert data.instructions == {"file": "content"}
        assert data.mcp_servers == []
        assert data.custom_agents == ["agent1"]
        assert data.env_vars == {"VAR": "val"}
        assert data.workspace_info == {"languages": ["python"]}
        assert data.estimated_context_tokens == 500

    def test_manifest_data_is_dataclass(self):
        """Test that ManifestData is a dataclass."""
        from dataclasses import is_dataclass
        assert is_dataclass(ManifestData)
