"""uc build — generate a project from a code-based declaration.

Composition:

    outward(
        write_project(
            verify_plan(
                generate(
                    prepare_build(
                        load_declaration_module(
                            inward(host_input)
                        )
                    )
                )
            )
        )
    )
"""

from __future__ import annotations

from pathlib import Path

from ..thing import is_thing
from .declaration import load_declaration_module
from .generate import generate
from .verify_plan import verify_plan
from .write_fs import write_project


def prepare_build(thing):
    """Turn a loaded program declaration into a generate-able new command."""
    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("prepare_build:rejected-non-thing",),
            "state": "invalid",
        }
    if thing["state"] in {"invalid", "absent", "false"}:
        return {
            **thing,
            "evidence": (*thing["evidence"], "prepare_build:skipped"),
            "state": thing["state"],
        }

    value = thing["value"]
    if not isinstance(value, dict) or value.get("kind") != "program":
        return {
            **thing,
            "evidence": (*thing["evidence"], "prepare_build:not-program"),
            "state": "invalid",
        }

    declaration = value.get("declaration")
    if not isinstance(declaration, dict):
        return {
            **thing,
            "evidence": (*thing["evidence"], "prepare_build:missing-declaration"),
            "state": "invalid",
        }

    parent = value.get("parent") or str(Path.cwd())
    name = value.get("project_name") or declaration["name"]
    project_path = Path(parent).expanduser().resolve() / name
    if project_path.exists():
        return {
            **thing,
            "value": {
                **value,
                "command": "new",
                "name": name,
                "package": declaration["package"],
                "project_path": str(project_path),
                "features": tuple(f["name"] for f in declaration["features"]),
                "program_declaration": declaration,
            },
            "evidence": (*thing["evidence"], "prepare_build:project-exists"),
            "state": "invalid",
        }

    return {
        **thing,
        "value": {
            **value,
            "command": "new",
            "name": name,
            "parent": str(Path(parent).expanduser().resolve()),
            "package": declaration["package"],
            "project_path": str(project_path),
            "features": tuple(f["name"] for f in declaration["features"]),
            "program_declaration": declaration,
        },
        "evidence": (*thing["evidence"], "prepare_build:ok"),
        "state": "formed",
    }


def run_build(thing):
    """Full build pipeline. One thing in, one thing out."""
    from ..boundary import outward

    return outward(
        write_project(
            verify_plan(
                generate(
                    prepare_build(
                        load_declaration_module(thing)
                    )
                )
            )
        )
    )
