"""Tests for the injector — end-to-end: workspace → files written."""

import json
import tempfile
from pathlib import Path

from agent_context.injector import inject


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
