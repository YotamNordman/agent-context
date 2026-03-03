"""Tests for workspace analyzer."""

import json
import tempfile
from pathlib import Path

from agent_context.analyzer import analyze


def _make_workspace(files: dict[str, str]) -> Path:
    """Create a temp workspace with given files."""
    tmp = Path(tempfile.mkdtemp())
    for path, content in files.items():
        p = tmp / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return tmp


class TestPythonDetection:
    def test_detects_python_from_pyproject(self):
        ws = _make_workspace({"pyproject.toml": '[project]\nname = "myapp"\n'})
        info = analyze(ws)
        assert "python" in info.languages
        assert info.package_name == "myapp"

    def test_detects_fastapi(self):
        ws = _make_workspace({"pyproject.toml": 'dependencies = ["fastapi", "aiosqlite"]'})
        info = analyze(ws)
        assert "fastapi" in info.frameworks
        assert "aiosqlite" in info.frameworks

    def test_detects_pytest(self):
        ws = _make_workspace({
            "pyproject.toml": '[tool.pytest.ini_options]\ntestpaths = ["tests"]',
            "tests/__init__.py": "",
        })
        info = analyze(ws)
        assert info.test_runner == "pytest"
        assert "pytest" in info.test_command

    def test_detects_ruff(self):
        ws = _make_workspace({"pyproject.toml": "[tool.ruff]\ntarget-version = 'py311'"})
        info = analyze(ws)
        assert info.lint_command is not None
        assert "ruff" in info.lint_command

    def test_detects_src_layout(self):
        ws = _make_workspace({"src/myapp/__init__.py": "", "pyproject.toml": ""})
        info = analyze(ws)
        assert "src/" in info.source_dirs

    def test_no_python_in_empty_dir(self):
        ws = _make_workspace({"README.md": "# hello"})
        info = analyze(ws)
        assert "python" not in info.languages


class TestJavascriptDetection:
    def test_detects_js_from_package_json(self):
        ws = _make_workspace({"package.json": json.dumps({"name": "myapp"})})
        info = analyze(ws)
        assert "javascript" in info.languages

    def test_detects_vite(self):
        ws = _make_workspace({
            "package.json": json.dumps({"devDependencies": {"vite": "^6.0"}}),
        })
        info = analyze(ws)
        assert "vite" in info.frameworks

    def test_detects_playwright(self):
        ws = _make_workspace({
            "package.json": json.dumps({
                "devDependencies": {"@playwright/test": "^1.58"},
                "scripts": {"test": "npx playwright test"},
            }),
            "tests/e2e.spec.js": "",
        })
        info = analyze(ws)
        assert info.test_runner == "playwright"
        assert info.test_command == "npx playwright test"

    def test_detects_build_command(self):
        ws = _make_workspace({
            "package.json": json.dumps({"scripts": {"build": "vite build"}}),
        })
        info = analyze(ws)
        assert info.build_command == "npm run build"


class TestInfraDetection:
    def test_detects_dockerfile(self):
        ws = _make_workspace({"Dockerfile": "FROM python:3.11"})
        info = analyze(ws)
        assert info.has_dockerfile is True

    def test_detects_k8s_dir(self):
        ws = _make_workspace({"k3s/deployment.yaml": "apiVersion: apps/v1"})
        info = analyze(ws)
        assert info.has_k8s_manifests is True

    def test_detects_k8s_yaml(self):
        ws = _make_workspace({"deploy.yaml": "apiVersion: apps/v1\nkind: Deployment"})
        info = analyze(ws)
        assert info.has_k8s_manifests is True

    def test_detects_ci(self):
        ws = _make_workspace({".github/workflows/ci.yml": "name: CI"})
        info = analyze(ws)
        assert info.has_ci is True

    def test_no_infra_in_plain_repo(self):
        ws = _make_workspace({"README.md": "hello"})
        info = analyze(ws)
        assert info.has_dockerfile is False
        assert info.has_k8s_manifests is False
