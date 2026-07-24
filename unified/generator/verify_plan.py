"""Verify a generation plan before any write boundary runs."""

from __future__ import annotations

from ..thing import is_thing


def verify_plan(thing):
    """Check that the plan is complete and coherent. No filesystem effects."""
    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("verify_plan:rejected-non-thing",),
            "state": "invalid",
        }

    if thing["state"] in {"invalid", "absent", "false"}:
        return {
            **thing,
            "evidence": (*thing["evidence"], "verify_plan:not-run"),
            "state": thing["state"],
        }

    value = thing["value"]
    if not isinstance(value, dict):
        return {
            **thing,
            "evidence": (*thing["evidence"], "verify_plan:value-not-map"),
            "state": "invalid",
        }

    files = value.get("files")
    if not isinstance(files, dict) or not files:
        return {
            **thing,
            "evidence": (*thing["evidence"], "verify_plan:no-files"),
            "state": "invalid",
        }

    if any(not isinstance(k, str) or not isinstance(v, str) for k, v in files.items()):
        return {
            **thing,
            "evidence": (*thing["evidence"], "verify_plan:bad-file-entry"),
            "state": "invalid",
        }

    if any(".." in part or part.startswith("/") for path in files for part in path.split("/")):
        return {
            **thing,
            "evidence": (*thing["evidence"], "verify_plan:unsafe-path"),
            "state": "invalid",
        }

    mode = value.get("write_mode")
    if mode not in {"create_project", "update_project"}:
        return {
            **thing,
            "evidence": (*thing["evidence"], "verify_plan:bad-write-mode"),
            "state": "invalid",
        }

    project_path = value.get("project_path")
    if not isinstance(project_path, str) or not project_path:
        return {
            **thing,
            "evidence": (*thing["evidence"], "verify_plan:missing-project-path"),
            "state": "invalid",
        }

    # Syntax-check every Python file in the plan.
    for rel, content in files.items():
        if rel.endswith(".py"):
            try:
                compile(content, rel, "exec")
            except SyntaxError as exc:
                return {
                    **thing,
                    "evidence": (
                        *thing["evidence"],
                        f"verify_plan:syntax-error:{rel}",
                        f"verify_plan:syntax:{exc.msg}",
                    ),
                    "state": "invalid",
                }

    return {
        **thing,
        "evidence": (
            *thing["evidence"],
            f"verify_plan:files:{len(files)}",
            "verify_plan:pass",
        ),
        "state": "valid",
    }
