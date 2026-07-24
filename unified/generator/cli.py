"""Host CLI for the Unified Code generator.

Composition (L2):

    outward(write_project(verify_plan(generate(validate(inward(host_input))))))
"""

from __future__ import annotations

import sys
from pathlib import Path

from ..boundary import host_render, inward, outward
from .generate import generate
from .validate import validate
from .verify_plan import verify_plan
from .write_fs import write_project


def run_command(thing):
    """Run the full generator pipeline. One thing in, one thing out."""
    return outward(write_project(verify_plan(generate(validate(thing)))))


def host_main(argv=None):
    """Process entry for the `uc` console script.

    When invoked by the console script (argv is None), exits with a status
    code. When invoked from tests with an explicit argv list, returns the
    code without raising SystemExit.
    """
    explicit = argv is not None
    argv = list(sys.argv[1:] if argv is None else argv)
    payload = _parse_argv(argv)
    result = run_command(inward(payload))
    code = 0 if result.get("state") == "valid" else 1
    # Host-edge rendering only after outward has marked the result.
    sys.stdout.write(host_render(result))
    sys.stdout.write("\n")
    if code == 0:
        value = result.get("value")
        if isinstance(value, dict):
            mode = value.get("write_mode")
            path = value.get("project_path")
            if mode == "create_project" and path:
                sys.stderr.write(f"uc: created {path}\n")
            elif mode == "update_project" and path:
                feature = value.get("feature")
                sys.stderr.write(f"uc: added {feature!r} to {path}\n")
    if explicit:
        return code
    raise SystemExit(code)


def _parse_argv(argv: list[str]) -> dict:
    if not argv:
        return {"command": None, "error": "missing-command"}
    command = argv[0]
    if command == "new":
        if len(argv) != 2:
            return {"command": "new", "name": argv[1] if len(argv) > 1 else None, "parent": None, "error": "usage-new"}
        name = argv[1]
        parent = str(Path.cwd())
        return {"command": "new", "name": name, "parent": parent}
    if command == "add":
        if len(argv) != 2:
            return {
                "command": "add",
                "name": argv[1] if len(argv) > 1 else None,
                "project_root": str(Path.cwd()),
                "error": "usage-add",
            }
        return {
            "command": "add",
            "name": argv[1],
            "project_root": str(Path.cwd()),
        }
    return {"command": command, "error": "unknown-command"}


if __name__ == "__main__":
    raise SystemExit(host_main())
