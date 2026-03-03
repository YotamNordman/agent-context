"""Workspace analyzer — detects language, framework, test runner, and structure."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceInfo:
    """Detected workspace characteristics."""

    path: Path
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    test_runner: str | None = None
    test_command: str | None = None
    lint_command: str | None = None
    build_command: str | None = None
    has_dockerfile: bool = False
    has_k8s_manifests: bool = False
    has_ci: bool = False
    package_name: str | None = None
    source_dirs: list[str] = field(default_factory=list)
    test_dirs: list[str] = field(default_factory=list)


def analyze(workspace: Path) -> WorkspaceInfo:
    """Analyze a workspace directory and return detected characteristics."""
    info = WorkspaceInfo(path=workspace)

    _detect_python(workspace, info)
    _detect_javascript(workspace, info)
    _detect_docker(workspace, info)
    _detect_k8s(workspace, info)
    _detect_ci(workspace, info)

    logger.info(
        "Analyzed %s: langs=%s frameworks=%s tests=%s",
        workspace,
        info.languages,
        info.frameworks,
        info.test_runner,
    )
    return info


def _detect_python(workspace: Path, info: WorkspaceInfo) -> None:
    pyproject = workspace / "pyproject.toml"
    setup_py = workspace / "setup.py"
    requirements = workspace / "requirements.txt"

    if not (pyproject.exists() or setup_py.exists() or requirements.exists()):
        if not list(workspace.glob("*.py")) and not list(workspace.glob("src/**/*.py")):
            return

    info.languages.append("python")

    # Detect source directory
    if (workspace / "src").is_dir():
        info.source_dirs.append("src/")
    elif any(workspace.glob("*.py")):
        info.source_dirs.append("./")

    # Detect test directory
    for test_dir in ["tests", "test"]:
        if (workspace / test_dir).is_dir():
            info.test_dirs.append(f"{test_dir}/")
            break

    # Parse pyproject.toml for details
    if pyproject.exists():
        content = pyproject.read_text()
        if "fastapi" in content.lower():
            info.frameworks.append("fastapi")
        if "django" in content.lower():
            info.frameworks.append("django")
        if "flask" in content.lower():
            info.frameworks.append("flask")
        if "aiosqlite" in content.lower():
            info.frameworks.append("aiosqlite")

        # Extract package name
        for line in content.splitlines():
            if line.strip().startswith("name"):
                name = line.split("=", 1)[1].strip().strip('"').strip("'")
                info.package_name = name
                break

        # Detect test runner
        if "pytest" in content:
            info.test_runner = "pytest"
            src = " ".join(info.source_dirs) if info.source_dirs else "src/"
            tst = " ".join(info.test_dirs) if info.test_dirs else "tests/"
            info.test_command = f"uv run pytest {tst}-v"
            info.lint_command = f"uv run ruff check {src}{tst}"

        if "ruff" in content:
            info.lint_command = info.lint_command or "uv run ruff check ."


def _detect_javascript(workspace: Path, info: WorkspaceInfo) -> None:
    pkg_json = workspace / "package.json"
    if not pkg_json.exists():
        return

    info.languages.append("javascript")
    info.source_dirs.append("./")

    try:
        pkg = json.loads(pkg_json.read_text())
    except (json.JSONDecodeError, OSError):
        return

    # Detect frameworks
    all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    if "react" in all_deps:
        info.frameworks.append("react")
    if "vue" in all_deps:
        info.frameworks.append("vue")
    if "vite" in all_deps:
        info.frameworks.append("vite")
    if "@playwright/test" in all_deps:
        info.test_runner = "playwright"
        info.test_command = "npx playwright test"
    if "jest" in all_deps:
        info.test_runner = "jest"
        info.test_command = "npm test"
    if "vitest" in all_deps:
        info.test_runner = "vitest"
        info.test_command = "npm test"

    # Build command
    scripts = pkg.get("scripts", {})
    if "build" in scripts:
        info.build_command = "npm run build"
    if "test" in scripts and not info.test_command:
        info.test_command = "npm test"

    # Test directories
    if (workspace / "tests").is_dir():
        info.test_dirs.append("tests/")
    elif (workspace / "__tests__").is_dir():
        info.test_dirs.append("__tests__/")


def _detect_docker(workspace: Path, info: WorkspaceInfo) -> None:
    dockerfiles = list(workspace.glob("Dockerfile*")) + list(workspace.glob("**/Dockerfile"))
    if dockerfiles:
        info.has_dockerfile = True


def _detect_k8s(workspace: Path, info: WorkspaceInfo) -> None:
    k8s_dirs = ["k3s", "k8s", "kubernetes", "manifests", "charts", "helm"]
    for d in k8s_dirs:
        if (workspace / d).is_dir():
            info.has_k8s_manifests = True
            return
    # Check for yaml files with apiVersion
    for yaml_file in list(workspace.glob("*.yaml")) + list(workspace.glob("*.yml")):
        try:
            if "apiVersion:" in yaml_file.read_text()[:200]:
                info.has_k8s_manifests = True
                return
        except OSError:
            continue


def _detect_ci(workspace: Path, info: WorkspaceInfo) -> None:
    ci_paths = [
        workspace / ".github" / "workflows",
        workspace / ".gitlab-ci.yml",
        workspace / "Jenkinsfile",
    ]
    info.has_ci = any(p.exists() for p in ci_paths)
