"""Template renderer — generates instruction files from Jinja2 templates."""

from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .analyzer import WorkspaceInfo

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


def render_instructions(info: WorkspaceInfo, task_context: dict | None = None) -> dict[str, str]:
    """Render all applicable instruction files for the detected workspace.

    Returns a dict of {filename: content} for each instruction file to write.
    """
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )

    ctx = {**asdict(info), "task": task_context or {}}
    results: dict[str, str] = {}

    # AGENTS.md — primary instructions file (highest priority in Copilot CLI)
    results["AGENTS.md"] = _render(env, "AGENTS.md.j2", ctx)

    # Safety instructions (always, tiny)
    results["safety.instructions.md"] = _render(env, "safety.instructions.md.j2", ctx)

    # Testing (if test runner detected)
    if info.test_runner:
        results["testing.instructions.md"] = _render(env, "testing.instructions.md.j2", ctx)

    # Custom agents — build and review roles
    job_type = (task_context or {}).get("job_type", "build")
    desc = (task_context or {}).get("description", "")
    if job_type == "review" or "review" in str(desc):
        results["review.agent.md"] = _render(env, "review.agent.md.j2", ctx)
    else:
        results["build.agent.md"] = _render(env, "build.agent.md.j2", ctx)

    # MCP config
    results["mcp.json"] = _render(env, "mcp.json.j2", ctx)

    return results


def _render(env: Environment, template_name: str, ctx: dict) -> str:
    try:
        tmpl = env.get_template(template_name)
        return tmpl.render(**ctx)
    except Exception as e:
        logger.warning("Failed to render %s: %s", template_name, e)
        return ""
