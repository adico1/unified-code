"""Host CLI for the Unified Code generator.

Process edge only for argv/stdout. Kernel pipelines are Thing→Thing.
"""

from __future__ import annotations

import sys
from pathlib import Path

from ..boundary import host_render, inward
from ..clock import LIMIT_NS
from .generate import generate
from .validate import validate
from .verify_plan import verify_plan
from .write_fs import write_project


def run_command(thing):
    """Generator pipeline for new/add. One thing in, one thing out."""
    from ..boundary import outward

    return outward(write_project(verify_plan(generate(validate(thing)))))


def host_main(argv=None):
    """OS process edge for `uc` — not a kernel Part."""
    explicit = argv is not None
    argv = list(sys.argv[1:] if argv is None else argv)
    payload = _parse_argv(argv)
    command = payload.get("command")

    if command == "benchmark":
        from .benchmark import run_benchmark

        result = run_benchmark(inward(payload))
    elif command == "build":
        from .build import run_build

        result = run_build(inward(payload))
    elif command == "gauntlet":
        from .gauntlet import run_gauntlet

        result = run_gauntlet(inward(payload))
    else:
        result = run_command(inward(payload))

    code = 0 if result.get("state") == "valid" else 1
    sys.stdout.write(host_render(result))
    sys.stdout.write("\n")

    if isinstance(result.get("value"), dict):
        value = result["value"]
        if command == "benchmark":
            new = value.get("new") or {}
            add = value.get("add") or {}
            sys.stderr.write(
                f"L9 {str(value.get('l9_verdict', 'fail')).upper()}: "
                f"new p95={new.get('p95_ns')} ns, "
                f"add p95={add.get('p95_ns')} ns, "
                f"limit={LIMIT_NS} ns\n"
            )
        elif command == "gauntlet":
            sys.stderr.write(
                f"GAUNTLET {str(value.get('verdict', 'fail')).upper()}: "
                f"passed={value.get('checks_passed')}/"
                f"{value.get('checks_executed')} "
                f"failed={value.get('checks_failed')} "
                f"duration_ns={value.get('duration_ns')}\n"
            )
        elif code == 0:
            path = value.get("project_path")
            if value.get("write_mode") == "create_project" and path:
                sys.stderr.write(f"uc: created {path}\n")
            elif value.get("write_mode") == "update_project" and path:
                sys.stderr.write(f"uc: added {value.get('feature')!r} to {path}\n")

    if explicit:
        return code
    raise SystemExit(code)


def _parse_argv(argv: list[str]) -> dict:
    if not argv:
        return {"command": None, "error": "missing-command"}
    command = argv[0]

    if command == "new":
        if len(argv) < 2:
            return {"command": "new", "name": None, "parent": None, "error": "usage-new"}
        name = argv[1]
        declaration = None
        i = 2
        while i < len(argv):
            if argv[i] == "--declaration" and i + 1 < len(argv):
                declaration = argv[i + 1]
                i += 2
                continue
            return {
                "command": "new",
                "name": name,
                "parent": str(Path.cwd()),
                "error": f"unknown-flag:{argv[i]}",
            }
        return {
            "command": "new",
            "name": name,
            "parent": str(Path.cwd()),
            "declaration": declaration,
        }

    if command == "add":
        if len(argv) < 2:
            return {
                "command": "add",
                "name": None,
                "project_root": str(Path.cwd()),
                "error": "usage-add",
            }
        name = argv[1]
        declaration = None
        i = 2
        while i < len(argv):
            if argv[i] == "--declaration" and i + 1 < len(argv):
                declaration = argv[i + 1]
                i += 2
                continue
            return {
                "command": "add",
                "name": name,
                "project_root": str(Path.cwd()),
                "error": f"unknown-flag:{argv[i]}",
            }
        return {
            "command": "add",
            "name": name,
            "project_root": str(Path.cwd()),
            "declaration": declaration,
        }

    if command == "build":
        # uc build path/to/declaration.py [--parent DIR] [--name NAME]
        if len(argv) < 2:
            return {"command": "build", "error": "usage-build"}
        declaration_path = argv[1]
        parent = str(Path.cwd())
        project_name = None
        i = 2
        while i < len(argv):
            if argv[i] == "--parent" and i + 1 < len(argv):
                parent = argv[i + 1]
                i += 2
                continue
            if argv[i] == "--name" and i + 1 < len(argv):
                project_name = argv[i + 1]
                i += 2
                continue
            return {
                "command": "build",
                "declaration_path": declaration_path,
                "error": f"unknown-flag:{argv[i]}",
            }
        return {
            "command": "build",
            "declaration_path": declaration_path,
            "parent": parent,
            "project_name": project_name,
        }

    if command == "gauntlet":
        # uc gauntlet [declaration.py|project_dir]
        target = argv[1] if len(argv) > 1 else None
        payload = {"command": "gauntlet", "mode": "framework"}
        if target:
            path = Path(target).expanduser().resolve()
            if path.is_file() and path.suffix == ".py":
                payload["mode"] = "declaration"
                payload["declaration_path"] = str(path)
            elif path.is_dir():
                payload["mode"] = "project"
                payload["project_path"] = str(path)
            else:
                payload["error"] = "gauntlet-target-not-found"
                payload["target"] = target
        else:
            # default: framework declaration
            root = Path(__file__).resolve().parents[2]
            decl = root / "examples" / "declarations" / "text_stats_v2.py"
            if not decl.is_file():
                decl = root / "examples" / "declarations" / "text_stats_program.py"
            payload["mode"] = "declaration"
            payload["declaration_path"] = str(decl)
        return payload

    if command == "benchmark":
        iterations = 10
        i = 1
        while i < len(argv):
            if argv[i] == "--iterations":
                if i + 1 >= len(argv):
                    return {
                        "command": "benchmark",
                        "iterations": None,
                        "error": "usage-benchmark",
                    }
                try:
                    iterations = int(argv[i + 1])
                except ValueError:
                    return {
                        "command": "benchmark",
                        "iterations": argv[i + 1],
                        "error": "usage-benchmark",
                    }
                i += 2
                continue
            return {
                "command": "benchmark",
                "iterations": iterations,
                "error": f"unknown-flag:{argv[i]}",
            }
        return {"command": "benchmark", "iterations": iterations}

    return {"command": command, "error": "unknown-command"}


if __name__ == "__main__":
    raise SystemExit(host_main())
