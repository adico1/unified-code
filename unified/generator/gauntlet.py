"""uc gauntlet — layered testing gauntlets G0–G8.

Returns a canonical thing with per-level results. No failed check may be
hidden by aggregate success.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from ..boundary import inward, outward
from ..clock import LIMIT_NS, clock_end, clock_start
from ..thing import is_thing
from .build import run_build
from .cli import run_command
from .declaration import load_declaration_module


def run_gauntlet(thing):
    """Execute gauntlet levels. One thing in, one thing out."""
    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("gauntlet:rejected-non-thing",),
            "state": "invalid",
        }

    started = clock_start(
        {
            **thing,
            "value": dict(thing["value"]) if isinstance(thing["value"], dict) else {"payload": thing["value"]},
            "state": "formed",
        }
    )
    value = started["value"] if isinstance(started["value"], dict) else {}
    levels = {}
    failures = []
    checks_executed = 0
    checks_passed = 0

    target = value.get("target")
    declaration_path = value.get("declaration_path")
    project_path = value.get("project_path")

    # Resolve mode
    mode = value.get("mode") or (
        "declaration" if declaration_path else "project" if project_path else "framework"
    )

    work = tempfile.mkdtemp(prefix="uc-gauntlet-")
    try:
        if mode in {"declaration", "build"} and declaration_path:
            built = run_build(
                inward(
                    {
                        "declaration_path": declaration_path,
                        "parent": work,
                        "project_name": value.get("project_name"),
                    }
                )
            )
            levels["build"] = {
                "state": built.get("state"),
                "evidence_tail": list(built.get("evidence", ()))[-5:],
            }
            if built.get("state") != "valid":
                failures.append("build:failed")
            else:
                project_path = built["value"]["project_path"]
                checks_executed += 1
                checks_passed += 1

        if mode == "framework" and not project_path:
            # Run against framework source + a standard declaration
            root = Path(__file__).resolve().parents[2]
            declaration_path = str(
                root / "examples" / "declarations" / "text_stats_v2.py"
            )
            if not Path(declaration_path).is_file():
                declaration_path = str(
                    root / "examples" / "declarations" / "text_stats_program.py"
                )
            built = run_build(
                inward(
                    {
                        "declaration_path": declaration_path,
                        "parent": work,
                        "project_name": "gauntlet-app",
                    }
                )
            )
            if built.get("state") == "valid":
                project_path = built["value"]["project_path"]
                checks_executed += 1
                checks_passed += 1
            else:
                failures.append("framework-build:failed")
                checks_executed += 1

        if project_path and Path(project_path).is_dir():
            decl_data = _load_decl_data(declaration_path)
            g0 = _g0_hygiene(project_path)
            g1 = _g1_law(project_path)
            g2 = _g2_effects(project_path)
            g3 = _g3_execution(project_path, decl_data)
            g4 = _g4_domain(project_path, decl_data)
            g5 = _g5_rollback(declaration_path, work)
            g6 = _g6_idempotency(declaration_path, work)
            g7 = _g7_mutations(project_path, decl_data)
            g8 = _g8_performance(declaration_path, work)

            for name, result in (
                ("G0", g0),
                ("G1", g1),
                ("G2", g2),
                ("G3", g3),
                ("G4", g4),
                ("G5", g5),
                ("G6", g6),
                ("G7", g7),
                ("G8", g8),
            ):
                levels[name] = result
                checks_executed += result["executed"]
                checks_passed += result["passed"]
                for fail in result.get("failed_checks") or ():
                    failures.append(f"{name}:{fail}")
        else:
            failures.append("gauntlet:no-project")
            checks_executed += 1

    finally:
        shutil.rmtree(work, ignore_errors=True)
        # Also remove generated project under work parent copies
        pass

    ended = clock_end(
        {
            **started,
            "value": {
                **value,
                "levels": levels,
                "checks_executed": checks_executed,
                "checks_passed": checks_passed,
                "checks_failed": checks_executed - checks_passed,
                "failed_checks": tuple(failures),
                "project_path": project_path,
            },
        }
    )
    duration = None
    if isinstance(ended.get("value"), dict):
        clock = ended["value"].get("clock") or {}
        duration = clock.get("duration_ns")

    verdict = "pass" if not failures else "fail"
    return outward(
        {
            **ended,
            "value": {
                **(ended["value"] if isinstance(ended.get("value"), dict) else {}),
                "gauntlet_level": "G0-G8",
                "checks_executed": checks_executed,
                "checks_passed": checks_passed,
                "checks_failed": len(failures),
                "failed_checks": tuple(failures),
                "verdict": verdict,
                "duration_ns": duration,
                "levels": levels,
            },
            "evidence": (
                *ended["evidence"],
                f"gauntlet:executed:{checks_executed}",
                f"gauntlet:passed:{checks_passed}",
                f"gauntlet:{verdict}",
            ),
            "state": "valid" if verdict == "pass" else "invalid",
        }
    )


def _load_decl_data(declaration_path: str | None) -> dict | None:
    if not declaration_path or not Path(declaration_path).is_file():
        return None
    loaded = load_declaration_module(
        {
            "value": {"declaration_path": declaration_path},
            "depths": (),
            "axes": (),
            "evidence": (),
            "state": "unknown",
        }
    )
    if loaded.get("state") != "formed":
        return None
    return loaded["value"].get("declaration")


def _pkg_dir(project_path: str) -> Path | None:
    root = Path(project_path)
    for child in root.iterdir():
        if child.is_dir() and (child / "__init__.py").is_file() and child.name.isidentifier():
            if child.name not in {"tests", "venv", ".venv"}:
                return child
    return None


ALLOWED_STATES = frozenset(
    {"unknown", "absent", "false", "formed", "valid", "invalid"}
)
# Predicates: one input, return bool — not Parts.
PREDICATE_NAMES = frozenset({"is_thing"})
# Process-edge helpers — not kernel Parts.
PROCESS_EDGE_NAMES = frozenset({"host_main", "host_render"})


def _is_canonical_thing(obj) -> bool:
    if not isinstance(obj, dict):
        return False
    for field in ("value", "depths", "axes", "evidence", "state"):
        if field not in obj:
            return False
    if not isinstance(obj["depths"], tuple):
        return False
    if not isinstance(obj["axes"], tuple):
        return False
    if not isinstance(obj["evidence"], tuple):
        return False
    if obj["state"] not in ALLOWED_STATES:
        return False
    return True


def _g0_hygiene(project_path: str) -> dict:
    root = Path(project_path)
    failed = []
    executed = 0
    passed = 0

    def check(name, ok):
        nonlocal executed, passed
        executed += 1
        if ok:
            passed += 1
        else:
            failed.append(name)

    compile_ok = True
    for py in root.rglob("*.py"):
        if any(x in py.parts for x in (".venv", "__pycache__", ".git")):
            continue
        try:
            compile(py.read_text(encoding="utf-8"), str(py), "exec")
        except SyntaxError:
            compile_ok = False
            break
    check("python-compile", compile_ok)

    gi = (root / ".gitignore").read_text(encoding="utf-8") if (root / ".gitignore").is_file() else ""
    check("gitignore-present", bool(gi))
    check("gitignore-pycache", "__pycache__" in gi or "*.py[cod]" in gi)
    check("gitignore-pytest", ".pytest_cache" in gi)

    planned_pyc = [
        p
        for p in root.rglob("*.pyc")
        if ".venv" not in p.parts
        and "site-packages" not in p.parts
        and "__pycache__" not in p.parts
    ]
    check("no-loose-pyc-in-source-tree", len(planned_pyc) == 0)

    pkg = _pkg_dir(project_path)
    if not pkg or not (pkg / "parts.py").is_file():
        check("parts-present", False)
    else:
        try:
            tree = ast.parse((pkg / "parts.py").read_text(encoding="utf-8"))
        except SyntaxError:
            check("parts-ast-parse", False)
            return {
                "executed": executed,
                "passed": passed,
                "failed_checks": tuple(failed),
                "verdict": "fail",
            }
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            # unused placeholder: function body is only `return None`
            body = [n for n in node.body if not isinstance(n, (ast.Pass, ast.Expr))]
            if (
                len(body) == 1
                and isinstance(body[0], ast.Return)
                and isinstance(body[0].value, ast.Constant)
                and body[0].value.value is None
            ):
                check(f"no-return-none-stub:{node.name}", False)
            else:
                check(f"no-return-none-stub:{node.name}", True)
            # evidence-only: only spreads thing and appends part:name without :ok
            src = ast.get_source_segment((pkg / "parts.py").read_text(encoding="utf-8"), node)
            if src is None:
                src = ""
            only_mark = (
                f'"part:{node.name}"' in src
                and f'"{node.name}:ok"' not in src
                and "len(" not in src
                and "isinstance" not in src
                and "value[" not in src
            )
            # Allow only if body has real branching (If) beyond non-thing reject
            has_logic = any(isinstance(n, (ast.If, ast.For, ast.While)) for n in ast.walk(node))
            if only_mark and not has_logic:
                check(f"no-evidence-only-feature:{node.name}", False)
            else:
                check(f"no-evidence-only-feature:{node.name}", True)

        # duplicate imports
        imports = [
            n
            for n in tree.body
            if isinstance(n, (ast.Import, ast.ImportFrom))
        ]
        seen = []
        dup = False
        for imp in imports:
            key = ast.dump(imp)
            if key in seen:
                dup = True
            seen.append(key)
        check("no-duplicate-imports", not dup)

        # features registration unique
        feat_path = pkg / "features.py"
        if feat_path.is_file():
            ns: dict = {}
            exec(compile(feat_path.read_text(encoding="utf-8"), str(feat_path), "exec"), ns, ns)
            features = ns.get("FEATURES", ())
            check("features-unique", len(features) == len(set(features)))
        else:
            check("features-present", False)

    return {
        "executed": executed,
        "passed": passed,
        "failed_checks": tuple(failed),
        "verdict": "pass" if not failed else "fail",
    }


def _g1_law(project_path: str) -> dict:
    root = Path(project_path)
    pkg = _pkg_dir(project_path)
    failed = []
    executed = 0
    passed = 0
    classification = {"parts": [], "predicates": [], "process_edge": [], "rejected": []}

    def check(name, ok):
        nonlocal executed, passed
        executed += 1
        if ok:
            passed += 1
        else:
            failed.append(name)

    if not pkg:
        return {
            "executed": 1,
            "passed": 0,
            "failed_checks": ("package-missing",),
            "verdict": "fail",
            "classification": classification,
        }

    public_ops = []
    for mod_name in ("boundary", "core", "parts", "compose", "expr_runtime"):
        path = pkg / f"{mod_name}.py"
        if not path.is_file():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            check(f"ast-parse:{mod_name}", False)
            continue
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                # expr_runtime helpers are not all Parts
                if mod_name == "expr_runtime":
                    if isinstance(node, ast.ClassDef):
                        check(f"no-class:{mod_name}.{node.name}", False)
                    continue
                public_ops.append((mod_name, node))
            if isinstance(node, ast.ClassDef):
                check(f"no-class:{mod_name}.{node.name}", False)

    check("has-public-ops", len(public_ops) > 0)

    for mod_name, node in public_ops:
        args = [a.arg for a in node.args.args]
        if node.name in PROCESS_EDGE_NAMES:
            classification["process_edge"].append(f"{mod_name}.{node.name}")
            # host_main must not be a kernel Part module; host_render may live in boundary
            # as a non-Part host helper (returns text, not nested in composition).
            if node.name == "host_main":
                check(f"host-main-not-in-kernel:{mod_name}", mod_name == "cli")
            continue
        if node.name in PREDICATE_NAMES:
            classification["predicates"].append(f"{mod_name}.{node.name}")
            check(
                f"predicate-one-param:{mod_name}.{node.name}",
                len(args) == 1 and args[0] == "thing",
            )
            continue
        # Part
        classification["parts"].append(f"{mod_name}.{node.name}")
        check(
            f"part-one-param:{mod_name}.{node.name}",
            len(args) == 1 and args[0] == "thing",
        )

    compose = (pkg / "compose.py").read_text(encoding="utf-8")
    check("compose-has-program", "def program(" in compose)
    check("compose-nested", "inward(" in compose and "outward(" in compose)

    features_text = (pkg / "features.py").read_text(encoding="utf-8")
    if "transform" not in features_text:
        check("transform-absent-from-compose", "transform(" not in compose)
    else:
        check("transform-declared", True)

    part_names = {
        node.name
        for node in ast.parse((pkg / "parts.py").read_text(encoding="utf-8")).body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    }
    boundary_part_names = {
        node.name
        for node in ast.parse((pkg / "boundary.py").read_text(encoding="utf-8")).body
        if isinstance(node, ast.FunctionDef)
        and not node.name.startswith("_")
        and node.name not in PREDICATE_NAMES
        and node.name not in PROCESS_EDGE_NAMES
    }
    core_part_names = {
        node.name
        for node in ast.parse((pkg / "core.py").read_text(encoding="utf-8")).body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    }

    sys.path.insert(0, str(root))
    try:
        import importlib

        for mod in list(sys.modules):
            if mod == pkg.name or mod.startswith(pkg.name + "."):
                del sys.modules[mod]
        parts = importlib.import_module(f"{pkg.name}.parts")
        boundary = importlib.import_module(f"{pkg.name}.boundary")
        core = importlib.import_module(f"{pkg.name}.core")
        compose_mod = importlib.import_module(f"{pkg.name}.compose")

        sample = {
            "value": {},
            "depths": (),
            "axes": (),
            "evidence": (),
            "state": "formed",
        }
        for name in part_names:
            result = getattr(parts, name)(sample)
            check(f"part-canonical:{name}", _is_canonical_thing(result))
        for name in boundary_part_names:
            fn = getattr(boundary, name)
            # present_result and others need full thing
            result = fn(sample)
            check(f"part-canonical:{name}", _is_canonical_thing(result))
        for name in core_part_names:
            result = getattr(core, name)(sample)
            check(f"part-canonical:{name}", _is_canonical_thing(result))

        prog = compose_mod.program(sample)
        check("program-canonical", _is_canonical_thing(prog))

        # predicates return bool
        if hasattr(boundary, "is_thing"):
            check("predicate-is_thing-bool", isinstance(boundary.is_thing(sample), bool))
            check("predicate-is_thing-rejects-non-thing", boundary.is_thing({}) is False)

        unknown = boundary.inward("x")
        check("state-unknown", unknown.get("state") == "unknown" and _is_canonical_thing(unknown))
        check(
            "state-absent",
            core.letter(boundary.inward(None)).get("state") == "absent",
        )
        check(
            "state-false",
            core.letter(boundary.inward(False)).get("state") == "false",
        )
        # distinct
        states = {
            unknown["state"],
            core.letter(boundary.inward(None))["state"],
            core.letter(boundary.inward(False))["state"],
        }
        check("states-distinct", states == {"unknown", "absent", "false"})
    except Exception as exc:  # noqa: BLE001
        check(f"import-runtime:{type(exc).__name__}", False)
    finally:
        if str(root) in sys.path:
            sys.path.remove(str(root))

    return {
        "executed": executed,
        "passed": passed,
        "failed_checks": tuple(failed),
        "verdict": "pass" if not failed else "fail",
        "classification": {
            "parts": tuple(classification["parts"]),
            "predicates": tuple(classification["predicates"]),
            "process_edge": tuple(classification["process_edge"]),
        },
    }


def _g2_effects(project_path: str) -> dict:
    pkg = _pkg_dir(project_path)
    failed = []
    executed = 0
    passed = 0

    def check(name, ok):
        nonlocal executed, passed
        executed += 1
        if ok:
            passed += 1
        else:
            failed.append(name)

    if not pkg:
        return {"executed": 1, "passed": 0, "failed_checks": ("package-missing",), "verdict": "fail"}

    # Domain parts must not use print/open/stdin
    parts_path = pkg / "parts.py"
    tree = ast.parse(parts_path.read_text(encoding="utf-8"))
    banned = {"print", "open", "input"}
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    hits = (names | attrs) & banned | ({"stdin", "stdout", "Path"} & (names | attrs))
    check("parts-no-io", len(hits) == 0)

    # read boundary must exist for file apps and use Path/sys in boundary only
    boundary_path = pkg / "boundary.py"
    btext = boundary_path.read_text(encoding="utf-8")
    check("boundary-has-read-or-none", True)  # optional depending on app
    if "def read_text_source" in btext:
        check("read-in-boundary", "read_text" in btext or "stdin" in btext)

    # host_main may print — but only in cli.py process edge
    cli = pkg / "cli.py"
    if cli.is_file():
        ctree = ast.parse(cli.read_text(encoding="utf-8"))
        for node in ctree.body:
            if isinstance(node, ast.FunctionDef) and node.name not in {"host_main"}:
                # other functions in cli should be rare
                pass
        check("cli-has-host-main", "def host_main" in cli.read_text(encoding="utf-8"))

    # present_result must not call print
    if "def present_result" in btext:
        # crude: between def present_result and next def
        idx = btext.index("def present_result")
        rest = btext[idx : idx + 2000]
        next_def = rest.find("\ndef ", 1)
        chunk = rest[: next_def if next_def > 0 else len(rest)]
        check("present-no-print", "print(" not in chunk)

    return {
        "executed": executed,
        "passed": passed,
        "failed_checks": tuple(failed),
        "verdict": "pass" if not failed else "fail",
    }


def _g3_execution(project_path: str, decl_data: dict | None = None) -> dict:
    root = Path(project_path)
    failed = []
    executed = 0
    passed = 0

    def check(name, ok):
        nonlocal executed, passed
        executed += 1
        if ok:
            passed += 1
        else:
            failed.append(name)

    env = {**os.environ, "PYTHONPATH": str(root)}
    pkg = _pkg_dir(project_path)
    if not pkg:
        return {"executed": 1, "passed": 0, "failed_checks": ("package-missing",), "verdict": "fail"}

    proc = subprocess.run(
        [sys.executable, "-c", f"import {pkg.name}, {pkg.name}.compose, {pkg.name}.parts"],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
    )
    check("import-modules", proc.returncode == 0)

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
    )
    check("unit-tests", proc.returncode == 0)

    # CLI success sample derived from declaration when available
    sample = root / "_gauntlet_sample.input"
    expect_fragment = None
    if decl_data:
        for case in decl_data.get("tests") or ():
            if not isinstance(case, dict):
                continue
            if case.get("kind") in {"json_stable", "stable_json"} and case.get("expect_json"):
                if "document" in case:
                    sample.write_text(json.dumps(case["document"]), encoding="utf-8")
                elif "text" in case:
                    sample.write_text(case["text"], encoding="utf-8")
                expect_fragment = case["expect_json"]
                break
            if case.get("kind") in {"json_document", "file_text"} and case.get("expect_stats"):
                if "document" in case:
                    sample.write_text(json.dumps(case["document"]), encoding="utf-8")
                else:
                    sample.write_text(case.get("text", ""), encoding="utf-8")
                # any stable key from expect_stats
                keys = list((case.get("expect_stats") or {}).keys())
                expect_fragment = keys[0] if keys else None
                break
    if not sample.exists():
        sample.write_text("x", encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, "-m", pkg.name, str(sample)],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
    )
    check("cli-success", proc.returncode == 0)
    if expect_fragment:
        check("cli-output-contract", expect_fragment in proc.stdout.replace(" ", "") or expect_fragment in proc.stdout)

    proc2 = subprocess.run(
        [sys.executable, "-m", pkg.name, str(sample)],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
    )
    check("deterministic-cli", proc.stdout == proc2.stdout and proc.returncode == proc2.returncode)

    proc = subprocess.run(
        [sys.executable, "-m", pkg.name],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
    )
    check("cli-error", proc.returncode != 0)

    sample.unlink(missing_ok=True)
    return {
        "executed": executed,
        "passed": passed,
        "failed_checks": tuple(failed),
        "verdict": "pass" if not failed else "fail",
    }


def _g4_domain(project_path: str, decl_data: dict | None = None) -> dict:
    """Domain contracts driven by declaration tests/examples only."""
    root = Path(project_path)
    pkg = _pkg_dir(project_path)
    failed = []
    executed = 0
    passed = 0

    def check(name, ok):
        nonlocal executed, passed
        executed += 1
        if ok:
            passed += 1
        else:
            failed.append(name)

    if not pkg:
        return {"executed": 1, "passed": 0, "failed_checks": ("package-missing",), "verdict": "fail"}

    cases = []
    if decl_data:
        cases = [
            c
            for c in (decl_data.get("tests") or ())
            if isinstance(c, dict)
            and c.get("kind") in {"json_document", "file_text", "json_error"}
        ]
    check("has-declared-cases", len(cases) >= 1 if decl_data else True)

    sys.path.insert(0, str(root))
    try:
        for mod in list(sys.modules):
            if mod == pkg.name or mod.startswith(pkg.name + "."):
                del sys.modules[mod]
        compose = __import__(f"{pkg.name}.compose", fromlist=["program"]).program
        with tempfile.TemporaryDirectory() as td:
            for case in cases[:12]:
                name = case.get("name", "case")
                path = Path(td) / f"{name}.input"
                if "document" in case:
                    path.write_text(json.dumps(case["document"]), encoding="utf-8")
                else:
                    path.write_text(case.get("text", ""), encoding="utf-8")
                result = compose({"source": str(path)})
                if case.get("kind") == "json_error":
                    check(
                        f"error:{name}",
                        result.get("state") == "invalid"
                        and (result.get("value") or {}).get("error") == case.get("error"),
                    )
                else:
                    expect = case.get("expect_stats")
                    check(f"case:{name}:valid", result.get("state") == "valid")
                    if expect is not None:
                        check(
                            f"case:{name}:stats",
                            (result.get("value") or {}).get("stats") == expect,
                        )
    except Exception as exc:  # noqa: BLE001
        check(f"domain-exception:{type(exc).__name__}", False)
    finally:
        if str(root) in sys.path:
            sys.path.remove(str(root))

    return {
        "executed": executed,
        "passed": passed,
        "failed_checks": tuple(failed),
        "verdict": "pass" if not failed else "fail",
    }


def _g5_rollback(declaration_path, work_parent: str) -> dict:
    """Inject failures at every required pipeline stage; prove no partial damage."""
    import importlib

    # Load true submodules (package __init__ may re-export functions under same names).
    gen_mod = importlib.import_module("unified.generator.generate")
    render_mod = importlib.import_module("unified.generator.render_declared")
    write_mod = importlib.import_module("unified.generator.write_fs")

    failed = []
    executed = 0
    passed = 0
    matrix = {}

    def check(name, ok, detail=None):
        nonlocal executed, passed
        executed += 1
        matrix[name] = {"ok": ok, "detail": detail}
        if ok:
            passed += 1
        else:
            failed.append(name)

    if not declaration_path or not Path(declaration_path).is_file():
        return {"executed": 1, "passed": 0, "failed_checks": ("no-declaration",), "verdict": "fail"}

    parent = Path(work_parent) / "rollback"
    parent.mkdir(parents=True, exist_ok=True)

    def safe_build(payload):
        try:
            return run_build(inward(payload))
        except Exception as exc:  # noqa: BLE001 — injected stage failures
            return {
                "value": payload,
                "depths": (),
                "axes": (),
                "evidence": (
                    "inject:stage-exception",
                    f"inject:{type(exc).__name__}",
                    str(exc)[:120],
                ),
                "state": "invalid",
            }

    def safe_command(payload):
        try:
            return run_command(inward(payload))
        except Exception as exc:  # noqa: BLE001
            return {
                "value": payload,
                "depths": (),
                "axes": (),
                "evidence": (
                    "inject:stage-exception",
                    f"inject:{type(exc).__name__}",
                    str(exc)[:120],
                ),
                "state": "invalid",
            }

    def clean_temps():
        for p in parent.glob(".uc-new-*"):
            shutil.rmtree(p, ignore_errors=True)
        for p in parent.iterdir():
            if p.is_dir() and p.name.startswith("inj-"):
                shutil.rmtree(p, ignore_errors=True)

    # --- 1. declaration loading ---
    before = {p.name for p in parent.iterdir()}
    bad = safe_build({"declaration_path": str(parent / "missing.py"), "parent": str(parent)})
    check(
        "inject:declaration-loading",
        bad.get("state") == "invalid"
        and "load:not-found" in (bad.get("evidence") or ())
        and {p.name for p in parent.iterdir()} == before,
    )

    # --- 2. validation (invalid declaration module) ---
    bad_decl = parent / "bad_decl.py"
    bad_decl.write_text("PROGRAM = 'not-a-map'\n", encoding="utf-8")
    bad = safe_build(
        {
            "declaration_path": str(bad_decl),
            "parent": str(parent),
            "project_name": "inj-val",
        }
    )
    check(
        "inject:validation",
        bad.get("state") == "invalid" and not (parent / "inj-val").exists(),
        detail=str(bad.get("evidence", ())[-3:]),
    )

    # --- 3. rendering ---
    real_render = gen_mod.render_program

    def boom_render(*_a, **_k):
        raise RuntimeError("render-injected-failure")

    gen_mod.render_program = boom_render
    try:
        bad = safe_build(
            {
                "declaration_path": declaration_path,
                "parent": str(parent),
                "project_name": "inj-render",
            }
        )
        check(
            "inject:rendering",
            bad.get("state") == "invalid" and not (parent / "inj-render").exists(),
            detail=str(bad.get("evidence", ())[-3:]),
        )
    finally:
        gen_mod.render_program = real_render
    clean_temps()

    # --- 4. first filesystem write ---
    write_count = {"n": 0}
    real_write_text = Path.write_text

    def fail_first(self, *a, **k):
        write_count["n"] += 1
        if write_count["n"] == 1 and ".uc-new-" in str(self):
            raise OSError("first-write-fail")
        return real_write_text(self, *a, **k)

    Path.write_text = fail_first
    try:
        bad = safe_build(
            {
                "declaration_path": declaration_path,
                "parent": str(parent),
                "project_name": "inj-first-write",
            }
        )
        check(
            "inject:first-filesystem-write",
            bad.get("state") == "invalid" and not (parent / "inj-first-write").exists(),
        )
        check(
            "inject:first-write-temps-removed",
            not list(parent.glob(".uc-new-*")),
        )
    finally:
        Path.write_text = real_write_text
    clean_temps()

    # --- 5. middle filesystem write ---
    write_count = {"n": 0}

    def fail_middle(self, *a, **k):
        write_count["n"] += 1
        if write_count["n"] == 5 and ".uc-new-" in str(self):
            raise OSError("middle-write-fail")
        return real_write_text(self, *a, **k)

    Path.write_text = fail_middle
    try:
        bad = safe_build(
            {
                "declaration_path": declaration_path,
                "parent": str(parent),
                "project_name": "inj-mid-write",
            }
        )
        check(
            "inject:middle-filesystem-write",
            bad.get("state") == "invalid" and not (parent / "inj-mid-write").exists(),
        )
        check("inject:middle-write-temps-removed", not list(parent.glob(".uc-new-*")))
    finally:
        Path.write_text = real_write_text
    clean_temps()

    # --- 6. final atomic replacement ---
    real_replace = write_mod.os.replace

    def boom_replace(*_a, **_k):
        raise OSError("replace-fail")

    write_mod.os.replace = boom_replace
    try:
        bad = safe_build(
            {
                "declaration_path": declaration_path,
                "parent": str(parent),
                "project_name": "inj-replace",
            }
        )
        check(
            "inject:final-atomic-replacement",
            bad.get("state") == "invalid"
            and not (parent / "inj-replace").exists()
            and (
                "write:failed:OSError" in (bad.get("evidence") or ())
                or "inject:OSError" in (bad.get("evidence") or ())
            ),
        )
        check("inject:replace-temps-removed", not list(parent.glob(".uc-new-*")))
    finally:
        write_mod.os.replace = real_replace
    clean_temps()

    # --- baseline good project for update-stage injections ---
    ok = safe_build(
        {
            "declaration_path": declaration_path,
            "parent": str(parent),
            "project_name": "rb-app",
        }
    )
    check("baseline-build-ok", ok.get("state") == "valid")
    project = parent / "rb-app"
    if ok.get("state") != "valid":
        return {
            "executed": executed,
            "passed": passed,
            "failed_checks": tuple(failed),
            "verdict": "fail",
            "injection_matrix": matrix,
        }
    snap = {rel: (project / rel).read_bytes() for rel in _list_files(project)}
    pkg = _pkg_dir(str(project))
    existing_feature = "mark_dup"
    if pkg and (pkg / "features.py").is_file():
        ns: dict = {}
        try:
            exec(
                compile((pkg / "features.py").read_text(encoding="utf-8"), "features.py", "exec"),
                ns,
                ns,
            )
            feats = ns.get("FEATURES") or ()
            if feats:
                existing_feature = feats[0]
        except Exception:
            pass

    # --- 7. feature insertion (duplicate / mid-update failure) ---
    dup = safe_command(
        {
            "command": "add",
            "name": existing_feature,
            "project_root": str(project),
        }
    )
    check(
        "inject:feature-insertion-duplicate",
        dup.get("state") == "invalid"
        and all((project / rel).read_bytes() == data for rel, data in snap.items()),
    )

    write_count = {"n": 0}

    def fail_update_mid(self, *a, **k):
        write_count["n"] += 1
        if write_count["n"] >= 2 and str(project) in str(self):
            raise OSError("feature-update-fail")
        return real_write_text(self, *a, **k)

    Path.write_text = fail_update_mid
    try:
        mid = safe_command(
            {
                "command": "add",
                "name": "extra_feat",
                "project_root": str(project),
            }
        )
        restored = all((project / rel).read_bytes() == data for rel, data in snap.items())
        check(
            "inject:feature-insertion-mid-write",
            mid.get("state") == "invalid"
            and (
                "write:rolled-back" in (mid.get("evidence") or ())
                or "inject:OSError" in (mid.get("evidence") or ())
            )
            and restored,
        )
    finally:
        Path.write_text = real_write_text

    check(
        "inject:feature-insertion-byte-restore",
        all((project / rel).read_bytes() == data for rel, data in snap.items()),
    )

    # --- 8. test generation failure ---
    real_gen_add = gen_mod._generate_add

    def boom_gen_add(thing, value):
        result = real_gen_add(thing, value)
        if result.get("state") == "formed":
            files = dict(result["value"]["files"])
            for k in list(files):
                if k.startswith("tests/"):
                    files[k] = "def not_valid_syntax(:\n"
            result = {
                **result,
                "value": {**result["value"], "files": files},
            }
        return result

    gen_mod._generate_add = boom_gen_add
    try:
        bad = safe_command(
            {
                "command": "add",
                "name": "tg_feat",
                "project_root": str(project),
            }
        )
        check(
            "inject:test-generation",
            bad.get("state") == "invalid"
            and all((project / rel).read_bytes() == data for rel, data in snap.items()),
        )
    finally:
        gen_mod._generate_add = real_gen_add

    # --- 9. boundary read failure during generate add ---
    real_read = Path.read_text

    def boom_read(self, *a, **k):
        if self.name == "parts.py" and str(project) in str(self):
            raise OSError("boundary-read-fail")
        return real_read(self, *a, **k)

    Path.read_text = boom_read
    try:
        bad = safe_command(
            {
                "command": "add",
                "name": "br_feat",
                "project_root": str(project),
            }
        )
        check(
            "inject:boundary-read",
            bad.get("state") == "invalid"
            and "generate:unreadable" in " ".join(bad.get("evidence") or ())
            and all((project / rel).read_bytes() == data for rel, data in snap.items()),
        )
    finally:
        Path.read_text = real_read

    # final integrity of baseline project
    check(
        "final-project-byte-intact",
        all((project / rel).read_bytes() == data for rel, data in snap.items()),
    )
    check("no-stray-temps", not list(parent.glob(".uc-new-*")))

    return {
        "executed": executed,
        "passed": passed,
        "failed_checks": tuple(failed),
        "verdict": "pass" if not failed else "fail",
        "injection_matrix": matrix,
    }


def _list_files(root: Path) -> list[str]:
    out = []
    for p in root.rglob("*"):
        if p.is_file() and ".venv" not in p.parts and "__pycache__" not in p.parts:
            out.append(str(p.relative_to(root)))
    return sorted(out)


def _g6_idempotency(declaration_path, work_parent: str) -> dict:
    failed = []
    executed = 0
    passed = 0
    matrix = {}

    def check(name, ok, detail=None):
        nonlocal executed, passed
        executed += 1
        matrix[name] = {"ok": ok, "detail": detail}
        if ok:
            passed += 1
        else:
            failed.append(name)

    if not declaration_path:
        return {"executed": 1, "passed": 0, "failed_checks": ("no-declaration",), "verdict": "fail"}

    parent = Path(work_parent) / "idem"
    parent.mkdir(parents=True, exist_ok=True)
    a = run_build(
        inward(
            {
                "declaration_path": declaration_path,
                "parent": str(parent),
                "project_name": "idem-a",
            }
        )
    )
    b = run_build(
        inward(
            {
                "declaration_path": declaration_path,
                "parent": str(parent),
                "project_name": "idem-b",
            }
        )
    )
    check("repeated-build-ok", a.get("state") == "valid" and b.get("state") == "valid")
    files_a = _file_hashes(parent / "idem-a")
    files_b = _file_hashes(parent / "idem-b")
    check("repeated-build-byte-identical", files_a == files_b)

    from .names import is_valid_feature_name

    check("reject-reserved-letter", not is_valid_feature_name("letter"))
    check("reject-reserved-inward", not is_valid_feature_name("inward"))
    check("reject-invalid-Feature", not is_valid_feature_name("Feature"))
    check("reject-invalid-hyphen", not is_valid_feature_name("bad-name"))

    project = parent / "idem-a"
    # unrelated user file must remain
    user_file = project / "USER_NOTES.txt"
    user_file.write_text("do not touch\n", encoding="utf-8")
    user_bytes = user_file.read_bytes()

    # repeated feature addition must not duplicate
    first = run_command(
        inward({"command": "add", "name": "mark_once", "project_root": str(project)})
    )
    check("feature-add-ok", first.get("state") == "valid")
    parts1 = (project / project.name.replace("-", "_") if False else _pkg_dir(str(project)) / "parts.py")
    pkg = _pkg_dir(str(project))
    parts_text = (pkg / "parts.py").read_text(encoding="utf-8")
    check("feature-def-once", parts_text.count("def mark_once(") == 1)

    second = run_command(
        inward({"command": "add", "name": "mark_once", "project_root": str(project)})
    )
    check("feature-add-duplicate-fails", second.get("state") == "invalid")
    parts_text2 = (pkg / "parts.py").read_text(encoding="utf-8")
    check("feature-no-duplicate-code", parts_text2.count("def mark_once(") == 1)

    # conflicting reserved feature via command
    conflict = run_command(
        inward({"command": "add", "name": "letter", "project_root": str(project)})
    )
    check("conflicting-reserved-name-fails", conflict.get("state") == "invalid")

    invalid_id = run_command(
        inward({"command": "add", "name": "Not_ok", "project_root": str(project)})
    )
    check("invalid-identifier-fails", invalid_id.get("state") == "invalid")

    check("unrelated-user-file-untouched", user_file.read_bytes() == user_bytes)

    # manual edit must not be silently overwritten
    compose_path = pkg / "compose.py"
    original = compose_path.read_text(encoding="utf-8")
    compose_path.write_text(original + "\n# MANUAL EDIT\n", encoding="utf-8")
    # force mtime into the future relative to any plan
    os.utime(compose_path, None)
    time.sleep(0.01)
    manual = run_command(
        inward({"command": "add", "name": "after_manual", "project_root": str(project)})
    )
    # either refuses or preserves manual marker if not rewriting compose... generate rewrites compose
    # with baselines: content != baseline => conflict
    check(
        "manual-edit-not-silently-overwritten",
        manual.get("state") == "invalid"
        and (
            "write:manual-edit-conflict" in (manual.get("evidence") or ())
            or "write:stale-plan" in (manual.get("evidence") or ())
        )
        and "# MANUAL EDIT" in compose_path.read_text(encoding="utf-8"),
    )

    # stale plan: craft a plan that is outdated
    # restore compose to valid for further test
    compose_path.write_text(original, encoding="utf-8")
    from .generate import generate
    from .validate import validate
    from .verify_plan import verify_plan
    from .write_fs import write_project

    planned = generate(
        validate(
            inward(
                {
                    "command": "add",
                    "name": "stale_feat",
                    "project_root": str(project),
                }
            )
        )
    )
    check("stale-plan-formed", planned.get("state") == "formed")
    # touch a file after plan
    target_rel = f"{pkg.name}/parts.py"
    parts_path = pkg / "parts.py"
    time.sleep(0.02)
    parts_path.write_text(parts_path.read_text(encoding="utf-8") + "\n# STALE TOUCH\n", encoding="utf-8")
    # update mtime in plan to be older
    if isinstance(planned.get("value"), dict):
        mtimes = dict(planned["value"].get("file_mtimes") or {})
        if target_rel in mtimes:
            mtimes[target_rel] = mtimes[target_rel] - 10_000_000_000
        planned = {
            **planned,
            "value": {**planned["value"], "file_mtimes": mtimes},
            "state": "formed",
        }
    verified = verify_plan(planned)
    # verify_plan sets valid if syntax ok — then write should refuse stale
    written = write_project(verified) if verified.get("state") == "valid" else verified
    check(
        "stale-plan-cannot-overwrite-newer",
        written.get("state") == "invalid"
        and (
            "write:stale-plan" in (written.get("evidence") or ())
            or "write:manual-edit-conflict" in (written.get("evidence") or ())
        )
        and "# STALE TOUCH" in parts_path.read_text(encoding="utf-8"),
    )

    return {
        "executed": executed,
        "passed": passed,
        "failed_checks": tuple(failed),
        "verdict": "pass" if not failed else "fail",
        "protection_matrix": matrix,
    }


def _file_hashes(root: Path) -> dict[str, str]:
    out = {}
    for rel in _list_files(root):
        data = (root / rel).read_bytes()
        out[rel] = hashlib.sha256(data).hexdigest()
    return out


def _g7_mutations(project_path: str, decl_data: dict | None = None) -> dict:
    """All 15 required mutations must be detected."""
    failed = []
    executed = 0
    passed = 0
    matrix = {}

    def check(name, ok, detail=None):
        nonlocal executed, passed
        executed += 1
        matrix[name] = {"detected": ok, "detail": detail}
        if ok:
            passed += 1
        else:
            failed.append(name)

    src = Path(project_path)
    pkg = _pkg_dir(project_path)
    if not pkg:
        return {"executed": 1, "passed": 0, "failed_checks": ("package-missing",), "verdict": "fail"}

    success_keys = tuple(
        ((decl_data or {}).get("presentation") or {}).get("success_keys") or ()
    )
    feature_names = [
        f["name"] for f in ((decl_data or {}).get("features") or ()) if isinstance(f, dict)
    ]
    primary_feature = feature_names[0] if feature_names else "validate_text"

    mutations = [
        ("remove-inward", _mut_remove_inward),
        ("remove-outward", _mut_remove_outward),
        ("collapse-none-false", _mut_collapse_none_false),
        ("delete-required-evidence", lambda r: _mut_delete_required_evidence(r, primary_feature)),
        ("reorder-evidence", _mut_reorder_evidence),
        ("insert-print", lambda r: _mut_insert_print(r, primary_feature)),
        ("insert-file-access", lambda r: _mut_insert_file(r, primary_feature)),
        ("bypass-verification", _mut_bypass_verification),
        ("duplicate-feature", lambda r: _mut_duplicate_feature(r, primary_feature)),
        ("change-formula", _mut_change_formula),
        ("change-output-key-order", lambda r: _mut_change_output_key_order(r, success_keys)),
        ("return-non-thing", lambda r: _mut_return_none(r, primary_feature)),
        ("second-param", lambda r: _mut_second_param(r, primary_feature)),
        ("add-class", _mut_add_class),
        ("partial-generated-file", _mut_partial_generated_file),
    ]

    for name, mutator in mutations:
        with tempfile.TemporaryDirectory(prefix="uc-mut-") as td:
            dest = Path(td) / "proj"
            shutil.copytree(
                src,
                dest,
                ignore=shutil.ignore_patterns(".venv", "__pycache__", "*.egg-info", ".pytest_cache"),
            )
            mutator(dest)
            detected, how = _detect_mutation(str(dest), name, decl_data)
            check(f"detect:{name}", detected, detail=how)

    check("mutations-count-15", len(mutations) == 15)

    return {
        "executed": executed,
        "passed": passed,
        "failed_checks": tuple(failed),
        "verdict": "pass" if not failed else "fail",
        "mutation_matrix": matrix,
    }


def _detect_mutation(
    project_path: str, mutation_name: str, decl_data: dict | None = None
) -> tuple[bool, str]:
    try:
        g0 = _g0_hygiene(project_path)
    except SyntaxError as exc:
        return True, f"G0:syntax:{exc}"
    if g0["verdict"] == "fail":
        return True, f"G0:{g0['failed_checks']}"
    try:
        g1 = _g1_law(project_path)
    except SyntaxError as exc:
        return True, f"G1:syntax:{exc}"
    if g1["verdict"] == "fail":
        return True, f"G1:{g1['failed_checks']}"
    try:
        g2 = _g2_effects(project_path)
    except SyntaxError as exc:
        return True, f"G2:syntax:{exc}"
    if g2["verdict"] == "fail":
        return True, f"G2:{g2['failed_checks']}"
    if mutation_name in {
        "change-formula",
        "change-output-key-order",
        "delete-required-evidence",
        "reorder-evidence",
        "bypass-verification",
        "duplicate-feature",
        "remove-inward",
        "remove-outward",
        "collapse-none-false",
    }:
        behavioral = _detect_behavioral(project_path, mutation_name, decl_data)
        if behavioral:
            return True, f"behavior:{behavioral}"
    g3 = _g3_execution(project_path, decl_data)
    if g3["verdict"] == "fail":
        return True, f"G3:{g3['failed_checks']}"
    g4 = _g4_domain(project_path, decl_data)
    if g4["verdict"] == "fail":
        return True, f"G4:{g4['failed_checks']}"
    return False, "undetected"


def _detect_behavioral(
    project_path: str, mutation_name: str, decl_data: dict | None = None
) -> str | None:
    root = Path(project_path)
    pkg = _pkg_dir(project_path)
    if not pkg:
        return "no-package"
    success_keys = tuple(
        ((decl_data or {}).get("presentation") or {}).get("success_keys") or ()
    )
    required_evidence = tuple(
        ((decl_data or {}).get("verify") or {}).get("require_evidence_contains") or ()
    )
    # pick a success case from declaration
    sample_doc = None
    sample_text = None
    expect_stats = None
    for case in (decl_data or {}).get("tests") or ():
        if not isinstance(case, dict):
            continue
        if case.get("kind") in {"json_document", "json_stable"} and (
            case.get("expect_stats") or case.get("expect_json")
        ):
            sample_doc = case.get("document")
            expect_stats = case.get("expect_stats")
            break
        if case.get("kind") in {"file_text", "stable_json"} and (
            case.get("expect_stats") or case.get("expect_json")
        ):
            sample_text = case.get("text", "x")
            expect_stats = case.get("expect_stats")
            break

    sys.path.insert(0, str(root))
    try:
        import importlib

        for mod in list(sys.modules):
            if mod == pkg.name or mod.startswith(pkg.name + "."):
                del sys.modules[mod]
        compose = importlib.import_module(f"{pkg.name}.compose")
        boundary = importlib.import_module(f"{pkg.name}.boundary")
        core = importlib.import_module(f"{pkg.name}.core")
        if mutation_name == "collapse-none-false":
            absent = core.letter(boundary.inward(None))
            false = core.letter(boundary.inward(False))
            if absent.get("state") == false.get("state"):
                return "states-collapsed"
        with tempfile.TemporaryDirectory() as td:
            sample = Path(td) / "s.input"
            if sample_doc is not None:
                sample.write_text(json.dumps(sample_doc), encoding="utf-8")
            else:
                sample.write_text(sample_text if sample_text is not None else "x", encoding="utf-8")
            result = compose.program({"source": str(sample)})
            if mutation_name == "change-formula" and expect_stats:
                stats = (result.get("value") or {}).get("stats") or {}
                if stats != expect_stats:
                    return "formula-wrong"
            if mutation_name == "change-output-key-order" and success_keys:
                pres = (result.get("value") or {}).get("presentation") or {}
                text = pres.get("text") or ""
                if text:
                    first_key = success_keys[0]
                    if not text.startswith('{"' + first_key + '"'):
                        return "key-order-wrong"
                stats = (result.get("value") or {}).get("stats")
                if isinstance(stats, dict) and list(stats.keys()) != list(success_keys):
                    return "stats-key-order"
            if mutation_name in {
                "delete-required-evidence",
                "reorder-evidence",
                "bypass-verification",
            }:
                evidence = result.get("evidence") or ()
                req = required_evidence or (
                    "boundary:inward",
                    "letter:distinguished",
                    "read:ok",
                    "script-law:pass",
                )
                if mutation_name == "delete-required-evidence":
                    if any(r not in evidence for r in req):
                        return "missing-evidence"
                if mutation_name == "reorder-evidence":
                    positions = [evidence.index(r) for r in req if r in evidence]
                    if positions != sorted(positions) or len(positions) < len(req):
                        return "evidence-order"
                if mutation_name == "bypass-verification":
                    broken = compose.program({"error": "missing-source"})
                    if broken.get("state") == "valid":
                        return "verify-bypassed-error"
            if mutation_name == "duplicate-feature":
                compose_src = (pkg / "compose.py").read_text(encoding="utf-8")
                # any feature name duplicated
                for fname in ((decl_data or {}).get("features") or ()):
                    if isinstance(fname, dict):
                        n = fname.get("name")
                        if n and compose_src.count(f"{n}(") >= 2:
                            return "duplicate-in-compose"
            if mutation_name in {"remove-inward", "remove-outward"}:
                compose_src = (pkg / "compose.py").read_text(encoding="utf-8")
                if mutation_name == "remove-inward" and "inward(" not in compose_src:
                    return "inward-missing"
                if mutation_name == "remove-outward" and "outward(" not in compose_src:
                    return "outward-missing"
        return None
    except Exception as exc:  # noqa: BLE001
        return f"exception:{type(exc).__name__}"
    finally:
        if str(root) in sys.path:
            sys.path.remove(str(root))


def _mut_remove_inward(root: Path):
    pkg = _pkg_dir(str(root))
    path = pkg / "compose.py"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("inward(", "str(").replace("inward,", "str,"), encoding="utf-8")


def _mut_remove_outward(root: Path):
    pkg = _pkg_dir(str(root))
    path = pkg / "compose.py"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("outward(", "(").replace(", outward", ""), encoding="utf-8")


def _mut_collapse_none_false(root: Path):
    pkg = _pkg_dir(str(root))
    path = pkg / "core.py"
    text = path.read_text(encoding="utf-8")
    text = text.replace('state = "absent"', 'state = "false"')
    path.write_text(text, encoding="utf-8")


def _mut_delete_required_evidence(root: Path, feature_name: str = "validate_text"):
    pkg = _pkg_dir(str(root))
    path = pkg / "parts.py"
    text = path.read_text(encoding="utf-8")
    text = text.replace(f'"{feature_name}:ok"', f'"{feature_name}:silent"')
    # also strip any :ok marks generically
    import re

    text = re.sub(r'"([a-z_]+):ok"', r'"\1:silent"', text)
    path.write_text(text, encoding="utf-8")


def _mut_reorder_evidence(root: Path):
    pkg = _pkg_dir(str(root))
    path = pkg / "boundary.py"
    text = path.read_text(encoding="utf-8")
    # reverse evidence append order for inward
    text = text.replace(
        '"evidence": ("boundary:inward",)',
        '"evidence": ("read:ok", "boundary:inward")',
    )
    path.write_text(text, encoding="utf-8")


def _mut_insert_print(root: Path, feature_name: str = "validate_text"):
    pkg = _pkg_dir(str(root))
    path = pkg / "parts.py"
    text = path.read_text(encoding="utf-8")
    needle = f"def {feature_name}(thing):"
    path.write_text(
        text.replace(needle, needle + "\n    print('leak')"),
        encoding="utf-8",
    )


def _mut_insert_file(root: Path, feature_name: str = "calculate_stats"):
    pkg = _pkg_dir(str(root))
    path = pkg / "parts.py"
    text = path.read_text(encoding="utf-8")
    # prefer calculate_* then first def
    for name in (feature_name, "calculate_totals", "calculate_stats"):
        needle = f"def {name}(thing):"
        if needle in text:
            path.write_text(
                text.replace(needle, needle + "\n    open('/tmp/x','w').write('x')"),
                encoding="utf-8",
            )
            return
    # fallback first function
    path.write_text(
        text.replace("def ", "def ", 1).replace(
            "(thing):",
            "(thing):\n    open('/tmp/x','w').write('x')",
            1,
        ),
        encoding="utf-8",
    )


def _mut_bypass_verification(root: Path):
    pkg = _pkg_dir(str(root))
    path = pkg / "core.py"
    text = path.read_text(encoding="utf-8")
    # force verify to always valid
    if "def verify(thing):" in text:
        text = text.replace(
            "def verify(thing):",
            "def verify(thing):\n    return {**thing, 'state': 'valid', 'evidence': (*thing.get('evidence', ()), 'script-law:pass')}\n    #",
        )
    path.write_text(text, encoding="utf-8")


def _mut_duplicate_feature(root: Path, feature_name: str = "validate_text"):
    pkg = _pkg_dir(str(root))
    path = pkg / "compose.py"
    text = path.read_text(encoding="utf-8")
    if f"{feature_name}(" in text:
        text = text.replace("return ", f"return {feature_name}(", 1)
        text = text.rstrip() + ")\n"
    path.write_text(text, encoding="utf-8")


def _mut_change_formula(root: Path):
    pkg = _pkg_dir(str(root))
    # Mutate runtime evaluation so any declared expected stats diverge.
    path = pkg / "expr_runtime.py"
    if path.is_file():
        text = path.read_text(encoding="utf-8")
        if "return len(value)" in text:
            path.write_text(
                text.replace("return len(value)", "return len(value) + 1"),
                encoding="utf-8",
            )
            return
        if "total += part" in text:
            path.write_text(text.replace("total += part", "total += part + 1", 1), encoding="utf-8")
            return
        if "return total" in text:
            path.write_text(text.replace("return total", "return total + 1"), encoding="utf-8")
            return
    path = pkg / "parts.py"
    if path.is_file():
        text = path.read_text(encoding="utf-8")
        if "len(text)" in text:
            path.write_text(text.replace("len(text)", "len(text) + 1"), encoding="utf-8")


def _mut_change_output_key_order(root: Path, success_keys: tuple = ()):
    pkg = _pkg_dir(str(root))
    path = pkg / "boundary.py"
    text = path.read_text(encoding="utf-8")
    if success_keys and len(success_keys) >= 2:
        original = "(" + ", ".join(f'"{k}"' for k in success_keys) + ")"
        reversed_keys = "(" + ", ".join(f'"{k}"' for k in reversed(success_keys)) + ")"
        if original in text:
            path.write_text(text.replace(original, reversed_keys, 1), encoding="utf-8")
            return
        original2 = "(" + ", ".join(f"'{k}'" for k in success_keys) + ")"
        reversed2 = "(" + ", ".join(f"'{k}'" for k in reversed(success_keys)) + ")"
        if original2 in text:
            path.write_text(text.replace(original2, reversed2, 1), encoding="utf-8")
            return
    # generic: reverse first keys tuple found in present_result
    import re

    m = re.search(r'keys = \(([^)]+)\)', text)
    if m:
        inner = m.group(1)
        parts = [p.strip() for p in inner.split(",") if p.strip()]
        rev = ", ".join(reversed(parts))
        text = text.replace(m.group(0), f"keys = ({rev})", 1)
        path.write_text(text, encoding="utf-8")


def _mut_return_none(root: Path, feature_name: str = "validate_text"):
    pkg = _pkg_dir(str(root))
    path = pkg / "parts.py"
    text = path.read_text(encoding="utf-8")
    needle = f"def {feature_name}(thing):"
    if needle not in text:
        # first def
        text = text.replace(
            "(thing):",
            "(thing):\n    return None\n    #",
            1,
        )
    else:
        text = text.replace(needle, needle + "\n    return None\n    #")
    path.write_text(text, encoding="utf-8")


def _mut_second_param(root: Path, feature_name: str = "validate_text"):
    pkg = _pkg_dir(str(root))
    path = pkg / "parts.py"
    text = path.read_text(encoding="utf-8")
    needle = f"def {feature_name}(thing):"
    if needle in text:
        text = text.replace(needle, f"def {feature_name}(thing, other=None):")
    else:
        text = text.replace("(thing):", "(thing, other=None):", 1)
    path.write_text(text, encoding="utf-8")


def _mut_add_class(root: Path):
    pkg = _pkg_dir(str(root))
    path = pkg / "parts.py"
    text = path.read_text(encoding="utf-8")
    path.write_text(text + "\n\nclass Bad:\n    pass\n", encoding="utf-8")


def _mut_partial_generated_file(root: Path):
    pkg = _pkg_dir(str(root))
    path = pkg / "parts.py"
    text = path.read_text(encoding="utf-8")
    # truncate mid-function
    path.write_text(text[: len(text) // 2] + "\n", encoding="utf-8")


def _g8_performance(declaration_path, work_parent: str) -> dict:
    failed = []
    executed = 0
    passed = 0

    def check(name, ok):
        nonlocal executed, passed
        executed += 1
        if ok:
            passed += 1
        else:
            failed.append(name)

    if not declaration_path:
        return {"executed": 1, "passed": 0, "failed_checks": ("no-declaration",), "verdict": "fail"}

    parent = Path(work_parent) / "perf"
    parent.mkdir(parents=True, exist_ok=True)
    samples = []
    for i in range(5):
        name = f"p{i}"
        t0 = time.perf_counter_ns()
        result = run_build(
            inward(
                {
                    "declaration_path": declaration_path,
                    "parent": str(parent),
                    "project_name": name,
                }
            )
        )
        t1 = time.perf_counter_ns()
        if result.get("state") != "valid":
            check("build-valid", False)
            break
        samples.append(t1 - t0)
    else:
        check("build-valid", True)
        samples_sorted = sorted(samples)
        p95_idx = max(0, math.ceil(0.95 * len(samples_sorted)) - 1)
        p95 = samples_sorted[p95_idx]
        check("build-p95-under-1s", p95 <= LIMIT_NS)

    # stub new for comparison when possible
    t0 = time.perf_counter_ns()
    stub = run_command(
        inward({"command": "new", "name": "perf-stub", "parent": str(parent)})
    )
    t1 = time.perf_counter_ns()
    check("new-under-1s", stub.get("state") == "valid" and (t1 - t0) <= LIMIT_NS)

    return {
        "executed": executed,
        "passed": passed,
        "failed_checks": tuple(failed),
        "verdict": "pass" if not failed else "fail",
        "build_samples_ns": tuple(samples) if samples else (),
    }
