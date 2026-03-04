"""Tests for the injector — end-to-end: workspace → files written."""

import json
import tempfile
from pathlib import Path

import pytest

from agent_context.injector import inject


def _make_workspace(files: dict[str, str]) -> Path:
    tmp = Path(tempfile.mkdtemp())
    for path, content in files.items():
        p = tmp / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return tmp


class TestInjection:
    def test_injects_agents_md(self):
        ws = _make_workspace({"pyproject.toml": '[project]\nname = "myapp"'})
        status = inject(ws)
        assert status["AGENTS.md"] == "written"
        assert (ws / "AGENTS.md").exists()
        content = (ws / "AGENTS.md").read_text()
        assert "Agent Instructions" in content

    def test_injects_build_agent_for_build_tasks(self):
        ws = _make_workspace({"pyproject.toml": ""})
        status = inject(ws, task_context={"job_type": "copilot-auto"})
        assert status["build.agent.md"] == "written"
        assert (ws / ".github" / "agents" / "build.agent.md").exists()

    def test_injects_review_agent_for_review_tasks(self):
        ws = _make_workspace({"pyproject.toml": ""})
        status = inject(ws, task_context={"job_type": "review"})
        assert status["review.agent.md"] == "written"
        assert (ws / ".github" / "agents" / "review.agent.md").exists()

    def test_injects_mcp_config(self):
        ws = _make_workspace({"pyproject.toml": ""})
        status = inject(ws)
        assert status["mcp.json"] == "written"
        assert (ws / ".github" / "mcp.json").exists()

    def test_injects_safety_instructions(self):
        ws = _make_workspace({"pyproject.toml": ""})
        status = inject(ws)
        assert status["safety.instructions.md"] == "written"

    def test_injects_testing_when_detected(self):
        ws = _make_workspace({
            "pyproject.toml": '[tool.pytest.ini_options]\ntestpaths = ["tests"]',
            "tests/__init__.py": "",
        })
        status = inject(ws)
        assert status["testing.instructions.md"] == "written"

    def test_no_testing_without_test_runner(self):
        ws = _make_workspace({"README.md": "hello"})
        status = inject(ws)
        assert "testing.instructions.md" not in status

    def test_fleet_mode_on_high_attempt_count(self):
        ws = _make_workspace({"pyproject.toml": ""})
        inject(ws, task_context={"attempt_count": 3}, overwrite=True)
        content = (ws / "AGENTS.md").read_text()
        assert "fleet" in content.lower() or "Fleet" in content

    def test_plan_first_on_retry(self):
        ws = _make_workspace({"pyproject.toml": ""})
        inject(ws, task_context={"attempt_count": 1}, overwrite=True)
        content = (ws / "AGENTS.md").read_text()
        assert "Plan First" in content or "plan" in content.lower()

    def test_feedback_injected(self):
        ws = _make_workspace({"pyproject.toml": ""})
        inject(ws, task_context={"feedback": "Missing error handling for null"}, overwrite=True)
        content = (ws / "AGENTS.md").read_text()
        assert "Missing error handling" in content

    def test_skips_existing_files(self):
        ws = _make_workspace({"pyproject.toml": "", "AGENTS.md": "# Custom"})
        status = inject(ws)
        assert status["AGENTS.md"] == "skipped"
        assert (ws / "AGENTS.md").read_text() == "# Custom"

    def test_overwrite_replaces(self):
        ws = _make_workspace({"pyproject.toml": "", "AGENTS.md": "# Old"})
        status = inject(ws, overwrite=True)
        assert status["AGENTS.md"] == "written"
        assert "Agent Instructions" in (ws / "AGENTS.md").read_text()

    def test_raises_on_missing_workspace(self):
        with pytest.raises(ValueError):
            inject("/nonexistent/path")

    def test_js_workspace(self):
        ws = _make_workspace({
            "package.json": json.dumps({
                "devDependencies": {"@playwright/test": "^1.58"},
                "scripts": {"test": "npx playwright test", "build": "vite build"},
            }),
        })
        inject(ws)
        content = (ws / "AGENTS.md").read_text()
        assert "javascript" in content.lower() or "playwright" in content.lower()
