"""Tests for the injector — end-to-end: workspace → files written."""

import json
import tempfile
from pathlib import Path

from agent_context.injector import inject, inject_custom_agents
from agent_context.profiles import AgentDefinition, ToolProfile


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


class TestCustomAgentInjection:
    """Tests for inject_custom_agents function."""

    def test_injects_oncall_custom_agents(self):
        """Test injecting custom agents from oncall profile."""
        ws = _make_workspace({"README.md": "# Test"})
        status = inject_custom_agents(ws, "oncall")

        assert status["incident-investigator.md"] == "written"
        assert status["tsg-finder.md"] == "written"

        # Verify files exist
        assert (ws / ".copilot" / "agents" / "incident-investigator.md").exists()
        assert (ws / ".copilot" / "agents" / "tsg-finder.md").exists()

    def test_injects_with_profile_object(self):
        """Test injecting using ToolProfile object instead of name."""
        ws = _make_workspace({"README.md": "# Test"})
        profile = ToolProfile(
            name="test",
            custom_agents=["incident-investigator"],
        )
        status = inject_custom_agents(ws, profile)

        assert status["incident-investigator.md"] == "written"
        assert (ws / ".copilot" / "agents" / "incident-investigator.md").exists()

    def test_skips_existing_agent_files(self):
        """Test that existing agent files are skipped by default."""
        ws = _make_workspace({
            ".copilot/agents/incident-investigator.md": "# Custom agent",
        })
        status = inject_custom_agents(ws, "oncall")

        # Should skip the existing file
        assert status["incident-investigator.md"] == "skipped"
        # Existing content preserved
        content = (ws / ".copilot" / "agents" / "incident-investigator.md").read_text()
        assert content == "# Custom agent"

    def test_overwrite_replaces_existing_agents(self):
        """Test that overwrite=True replaces existing agent files."""
        ws = _make_workspace({
            ".copilot/agents/incident-investigator.md": "# Old",
        })
        status = inject_custom_agents(ws, "oncall", overwrite=True)

        assert status["incident-investigator.md"] == "written"
        content = (ws / ".copilot" / "agents" / "incident-investigator.md").read_text()
        assert "incident-investigator" in content.lower()

    def test_agent_file_has_required_sections(self):
        """Test that agent files contain required sections."""
        ws = _make_workspace({"README.md": "# Test"})
        inject_custom_agents(ws, "oncall")

        content = (ws / ".copilot" / "agents" / "incident-investigator.md").read_text()
        assert "incident-investigator" in content
        assert "## Instructions" in content
        assert "## Allowed Tools" in content
        assert "## MCP Servers" in content

    def test_agent_file_formatting(self):
        """Test that agent files are properly formatted."""
        ws = _make_workspace({"README.md": "# Test"})
        inject_custom_agents(ws, "oncall")

        content = (ws / ".copilot" / "agents" / "tsg-finder.md").read_text()
        # Should have markdown header
        assert content.startswith("# tsg-finder")
        # Should have description
        assert "troubleshooting" in content.lower()
        # Should have tools listed
        assert "msdocs" in content

    def test_agent_injection_creates_directory(self):
        """Test that .copilot/agents directory is created if missing."""
        ws = _make_workspace({"README.md": "# Test"})
        inject_custom_agents(ws, "oncall")
        assert (ws / ".copilot" / "agents").is_dir()

    def test_raises_on_missing_workspace(self):
        """Test that missing workspace raises ValueError."""
        import pytest
        with pytest.raises(ValueError):
            inject_custom_agents("/nonexistent/path", "oncall")

    def test_raises_on_invalid_profile_name(self):
        """Test that invalid profile name raises ValueError."""
        import pytest
        ws = _make_workspace({"README.md": "# Test"})
        with pytest.raises(ValueError):
            inject_custom_agents(ws, "nonexistent-profile")

    def test_handles_empty_custom_agents_list(self):
        """Test that profiles with no custom agents return empty status."""
        ws = _make_workspace({"README.md": "# Test"})
        status = inject_custom_agents(ws, "base")

        # Should return empty dict (no agents to inject)
        assert status == {}

    def test_agent_not_found_returns_empty_status(self):
        """Test that missing agent is marked as empty in status."""
        ws = _make_workspace({"README.md": "# Test"})
        profile = ToolProfile(
            name="test",
            custom_agents=["nonexistent-agent"],
        )
        status = inject_custom_agents(ws, profile)

        assert status["nonexistent-agent.md"] == "empty"

    def test_multiple_agent_injection(self):
        """Test injecting multiple agents."""
        ws = _make_workspace({"README.md": "# Test"})
        status = inject_custom_agents(ws, "oncall")

        # Should inject both oncall agents
        written = sum(1 for v in status.values() if v == "written")
        assert written == 2

        # Both files should exist
        assert (ws / ".copilot" / "agents" / "incident-investigator.md").exists()
        assert (ws / ".copilot" / "agents" / "tsg-finder.md").exists()

    def test_agent_contains_description(self):
        """Test that agent file contains agent description."""
        ws = _make_workspace({"README.md": "# Test"})
        inject_custom_agents(ws, "oncall")

        content = (ws / ".copilot" / "agents" / "incident-investigator.md").read_text()
        # Check that description is in the file
        assert "Investigates" in content or "incident" in content.lower()

    def test_agent_contains_mcp_servers(self):
        """Test that agent file lists MCP servers."""
        ws = _make_workspace({"README.md": "# Test"})
        inject_custom_agents(ws, "oncall")

        content = (ws / ".copilot" / "agents" / "incident-investigator.md").read_text()
        # Check for MCP server names
        assert "icm" in content or "adx" in content
