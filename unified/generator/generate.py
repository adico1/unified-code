"""Produce generation plans as data. No filesystem writes."""

from __future__ import annotations

from pathlib import Path

from ..thing import is_thing
from .render import render_add_feature, render_new_project


def generate(thing):
    """Build a file plan inside the thing. Does not touch the filesystem for writes.

    Reads existing project files only when command is `add` (input boundary for
    project state). All outputs are plain data under value["files"].
    """
    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("generate:rejected-non-thing",),
            "state": "invalid",
        }

    if thing["state"] in {"invalid", "absent", "false"}:
        return {
            **thing,
            "evidence": (*thing["evidence"], "generate:skipped-invalid-input"),
            "state": thing["state"],
        }

    value = thing["value"]
    if not isinstance(value, dict):
        return {
            **thing,
            "evidence": (*thing["evidence"], "generate:value-not-map"),
            "state": "invalid",
        }

    command = value.get("command")
    if command == "new":
        return _generate_new(thing, value)
    if command == "add":
        return _generate_add(thing, value)
    return {
        **thing,
        "evidence": (*thing["evidence"], "generate:unknown-command"),
        "state": "invalid",
    }


def _generate_new(thing, value):
    package = value["package"]
    name = value["name"]
    features = tuple(value["features"])
    files = render_new_project(package, name, features)
    return {
        **thing,
        "value": {
            **value,
            "files": files,
            "write_mode": "create_project",
            "written": (),
        },
        "evidence": (
            *thing["evidence"],
            f"generate:files:{len(files)}",
            "generate:new-plan",
        ),
        "state": "formed",
    }


def _generate_add(thing, value):
    package = value["package"]
    project_path = Path(value["project_path"])
    feature = value["feature"]
    existing = tuple(value["features"])

    required = (
        f"{package}/features.py",
        f"{package}/parts.py",
        f"{package}/compose.py",
        "tests/test_signature.py",
        "tests/test_program.py",
        "pyproject.toml",
        f"{package}/boundary.py",
        f"{package}/core.py",
        f"{package}/__init__.py",
        f"{package}/__main__.py",
    )
    current: dict[str, str] = {}
    for rel in required:
        path = project_path / rel
        if not path.is_file():
            return {
                **thing,
                "evidence": (*thing["evidence"], f"generate:missing-file:{rel}"),
                "state": "invalid",
            }
        try:
            current[rel] = path.read_text(encoding="utf-8")
        except OSError:
            return {
                **thing,
                "evidence": (*thing["evidence"], f"generate:unreadable:{rel}"),
                "state": "invalid",
            }

    # Refuse if the feature function already appears as a def (ambiguous).
    parts_text = current[f"{package}/parts.py"]
    if f"def {feature}(" in parts_text:
        return {
            **thing,
            "evidence": (*thing["evidence"], "generate:feature-def-exists"),
            "state": "invalid",
        }

    project_name = project_path.name
    files = render_add_feature(package, project_name, existing, feature, current)
    return {
        **thing,
        "value": {
            **value,
            "files": files,
            "write_mode": "update_project",
            "features": (*existing, feature),
            "written": (),
        },
        "evidence": (
            *thing["evidence"],
            f"generate:files:{len(files)}",
            f"generate:add:{feature}",
        ),
        "state": "formed",
    }
