"""CLI entry point: python -m agent_context inject /workspace [options]"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from .injector import inject


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agent-context",
        description="Inject Copilot CLI instruction files into an agent workspace",
    )
    sub = parser.add_subparsers(dest="command")

    inject_cmd = sub.add_parser("inject", help="Analyze workspace and inject instructions")
    inject_cmd.add_argument("workspace", help="Path to workspace root")
    inject_cmd.add_argument("--task-id", help="Task ID for context")
    inject_cmd.add_argument("--task-desc", help="Task description")
    inject_cmd.add_argument("--acceptance-criteria", help="Acceptance criteria")
    inject_cmd.add_argument("--feedback", help="Previous review feedback")
    inject_cmd.add_argument("--project-id", help="Project identifier")
    inject_cmd.add_argument("--job-type", help="Job type: copilot-auto, review, script")
    inject_cmd.add_argument("--attempt-count", type=int, default=0, help="Number of previous attempts")
    inject_cmd.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    inject_cmd.add_argument("--verbose", "-v", action="store_true")
    inject_cmd.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    task_context = {}
    if args.task_id:
        task_context["task_id"] = args.task_id
    if args.task_desc:
        task_context["description"] = args.task_desc
    if args.acceptance_criteria:
        task_context["acceptance_criteria"] = args.acceptance_criteria
    if args.feedback:
        task_context["feedback"] = args.feedback
    if args.project_id:
        task_context["project_id"] = args.project_id
    if args.job_type:
        task_context["job_type"] = args.job_type
    task_context["attempt_count"] = args.attempt_count

    status = inject(
        args.workspace,
        task_context=task_context or None,
        overwrite=args.overwrite,
    )
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
