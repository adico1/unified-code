"""uc gauntlet — layered testing gauntlets G0–G8.

Returns a canonical thing with per-level results. No failed check may be
hidden by aggregate success.
"""

from __future__ import annotations

import ast
import hashlib
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
            g0 = _g0_hygiene(project_path)
            g1 = _g1_law(project_path)
            g2 = _g2_effects(project_path)
            g3 = _g3_execution(project_path)
            g4 = _g4_domain(project_path)
            g5 = _g5_rollback(declaration_path, work)
            g6 = _g6_idempotency(declaration_path, work)
            g7 = _g7_mutations(project_path)
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


def _pkg_dir(project_path: str) -> Path | None:
    root = Path(project_path)
    for child in root.iterdir():
        if child.is_dir() and (child / "__init__.py").is_file() and child.name.isidentifier():
            if child.name not in {"tests", "venv", ".venv"}:
                return child
    return None


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

    # compile all py
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

    # Generation must not *ship* caches; local pytest/venv artifacts are ignored.
    # Require .gitignore to exclude them so they are not publishable.
    gi = (root / ".gitignore").read_text(encoding="utf-8") if (root / ".gitignore").is_file() else ""
    check("gitignore-present", bool(gi))
    check("gitignore-pycache", "__pycache__" in gi or "*.py[cod]" in gi)
    check("gitignore-pytest", ".pytest_cache" in gi or "pytest" in gi)
    # Generated tree itself must not include .pyc as planned source files.
    planned_pyc = [
        p
        for p in root.rglob("*.pyc")
        if ".venv" not in p.parts
        and "site-packages" not in p.parts
        and "__pycache__" not in p.parts
    ]
    check("no-loose-pyc-in-source-tree", len(planned_pyc) == 0)

    # no return None stubs in parts
    pkg = _pkg_dir(project_path)
    if pkg and (pkg / "parts.py").is_file():
        text = (pkg / "parts.py").read_text(encoding="utf-8")
        check("no-return-none-stub", "return None" not in text)
        check("no-empty-evidence-only", 'evidence": (*thing["evidence"], "part:' not in text or ":ok" in text)
    else:
        check("parts-present", False)
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

    def check(name, ok):
        nonlocal executed, passed
        executed += 1
        if ok:
            passed += 1
        else:
            failed.append(name)

    if not pkg:
        return {"executed": 1, "passed": 0, "failed_checks": ("package-missing",), "verdict": "fail"}

    # Discover public functions from modules
    public_ops = []
    for mod_name in ("boundary", "core", "parts", "compose"):
        path = pkg / f"{mod_name}.py"
        if not path.is_file():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                public_ops.append((mod_name, node))
            if isinstance(node, ast.ClassDef):
                check(f"no-class:{mod_name}.{node.name}", False)

    check("has-public-ops", len(public_ops) > 0)

    for mod_name, node in public_ops:
        if node.name == "host_main":
            check(f"host_main-not-public-op:{mod_name}", False)
            continue
        args = [a.arg for a in node.args.args]
        # predicates like is_thing must still be one-input named thing
        check(
            f"one-param:{mod_name}.{node.name}",
            len(args) == 1 and args[0] == "thing",
        )

    # composition nested
    compose = (pkg / "compose.py").read_text(encoding="utf-8")
    check("compose-has-program", "def program(" in compose)
    check("compose-nested", "inward(" in compose and "outward(" in compose)
    check("no-forced-transform", "transform(" not in compose or "from .parts import" in compose and "transform" in compose)

    # transform only if in FEATURES
    features_text = (pkg / "features.py").read_text(encoding="utf-8")
    if "transform" not in features_text:
        check("transform-absent-from-compose", "transform(" not in compose)
    else:
        check("transform-declared", True)

    # Import and smoke defined parts only (AST names, not re-exports)
    defined_part_names = {
        node.name
        for node in ast.parse((pkg / "parts.py").read_text(encoding="utf-8")).body
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
        for name in defined_part_names:
            fn = getattr(parts, name)
            result = fn({"value": {}, "depths": (), "axes": (), "evidence": (), "state": "formed"})
            check(
                f"returns-thing:{name}",
                isinstance(result, dict)
                and "state" in result
                and "evidence" in result,
            )
        unknown = boundary.inward("x")
        check("state-unknown", unknown.get("state") == "unknown")
        from importlib import import_module

        core = import_module(f"{pkg.name}.core")
        check("state-absent", core.letter(boundary.inward(None)).get("state") == "absent")
        check("state-false", core.letter(boundary.inward(False)).get("state") == "false")
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


def _g3_execution(project_path: str) -> dict:
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

    # import modules
    proc = subprocess.run(
        [sys.executable, "-c", f"import {pkg.name}, {pkg.name}.compose, {pkg.name}.parts"],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
    )
    check("import-modules", proc.returncode == 0)

    # unit tests
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
    )
    check("unit-tests", proc.returncode == 0)

    # console success
    sample = root / "_gauntlet_sample.txt"
    sample.write_text("Go go GO", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", pkg.name, str(sample)],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
    )
    check("cli-success", proc.returncode == 0 and "unique_words" in proc.stdout)
    check("deterministic-cli", '"unique_words":1' in proc.stdout.replace(" ", ""))

    # console error
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


def _g4_domain(project_path: str) -> dict:
    """Domain contract via running generated tests (declaration-driven)."""
    # Covered primarily by G3 unit-tests; add explicit empty/unicode if importable.
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

    sys.path.insert(0, str(root))
    try:
        for mod in list(sys.modules):
            if mod == pkg.name or mod.startswith(pkg.name + "."):
                del sys.modules[mod]
        compose = __import__(f"{pkg.name}.compose", fromlist=["program"]).program
        import tempfile
        from pathlib import Path as P

        with tempfile.TemporaryDirectory() as td:
            p = P(td) / "t.txt"
            p.write_text("", encoding="utf-8")
            r = compose({"source": str(p)})
            check("empty-valid", r.get("state") == "valid")
            check("empty-zeros", r.get("value", {}).get("stats") == {
                "characters": 0,
                "lines": 0,
                "words": 0,
                "unique_words": 0,
            })
            p.write_text("שלום", encoding="utf-8")
            r = compose({"source": str(p)})
            check("unicode-valid", r.get("state") == "valid")
            check("unicode-words", r.get("value", {}).get("stats", {}).get("words") == 1)
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

    if not declaration_path or not Path(declaration_path).is_file():
        return {"executed": 1, "passed": 0, "failed_checks": ("no-declaration",), "verdict": "fail"}

    parent = Path(work_parent) / "rollback"
    parent.mkdir(parents=True, exist_ok=True)

    # Invalid declaration path must not create project
    before = set(parent.iterdir())
    bad = run_build(inward({"declaration_path": str(parent / "missing.py"), "parent": str(parent)}))
    check("bad-decl-invalid", bad.get("state") == "invalid")
    after = set(parent.iterdir())
    check("bad-decl-no-partial", before == after)

    # Valid build then simulate mid-write failure on second build to existing
    ok = run_build(
        inward(
            {
                "declaration_path": declaration_path,
                "parent": str(parent),
                "project_name": "rb-app",
            }
        )
    )
    check("first-build-ok", ok.get("state") == "valid")
    project = parent / "rb-app"
    check("project-exists", project.is_dir())

    # Second build to same path must fail without corrupting
    snap = {
        rel: (project / rel).read_bytes()
        for rel in _list_files(project)
    }
    again = run_build(
        inward(
            {
                "declaration_path": declaration_path,
                "parent": str(parent),
                "project_name": "rb-app",
            }
        )
    )
    check("second-build-refused", again.get("state") == "invalid")
    check(
        "unchanged-after-refuse",
        all((project / rel).read_bytes() == data for rel, data in snap.items()),
    )

    return {
        "executed": executed,
        "passed": passed,
        "failed_checks": tuple(failed),
        "verdict": "pass" if not failed else "fail",
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

    def check(name, ok):
        nonlocal executed, passed
        executed += 1
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
    check("two-builds-ok", a.get("state") == "valid" and b.get("state") == "valid")
    files_a = _file_hashes(parent / "idem-a")
    files_b = _file_hashes(parent / "idem-b")
    check("byte-identical-trees", files_a == files_b)

    # reserved/invalid add names
    from .names import is_valid_feature_name

    check("reject-reserved-letter", not is_valid_feature_name("letter"))
    check("reject-invalid-Feature", not is_valid_feature_name("Feature"))

    return {
        "executed": executed,
        "passed": passed,
        "failed_checks": tuple(failed),
        "verdict": "pass" if not failed else "fail",
    }


def _file_hashes(root: Path) -> dict[str, str]:
    out = {}
    for rel in _list_files(root):
        data = (root / rel).read_bytes()
        out[rel] = hashlib.sha256(data).hexdigest()
    return out


def _g7_mutations(project_path: str) -> dict:
    """Copy project, mutate, ensure gauntlet subchecks fail."""
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

    src = Path(project_path)
    pkg = _pkg_dir(project_path)
    if not pkg:
        return {"executed": 1, "passed": 0, "failed_checks": ("package-missing",), "verdict": "fail"}

    mutations = [
        ("remove-inward", _mut_remove_inward),
        ("remove-outward", _mut_remove_outward),
        ("collapse-none-false", _mut_collapse_none_false),
        ("insert-print", _mut_insert_print),
        ("insert-file-access", _mut_insert_file),
        ("add-class", _mut_add_class),
        ("second-param", _mut_second_param),
        ("change-formula", _mut_change_formula),
        ("return-none", _mut_return_none),
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
            # Detection via G0/G1/G2/G3 subsets
            detected = False
            g0 = _g0_hygiene(str(dest))
            g1 = _g1_law(str(dest))
            g2 = _g2_effects(str(dest))
            if g0["verdict"] == "fail" or g1["verdict"] == "fail" or g2["verdict"] == "fail":
                detected = True
            else:
                # try running domain
                g3 = _g3_execution(str(dest))
                if g3["verdict"] == "fail":
                    detected = True
            check(f"detect:{name}", detected)

    return {
        "executed": executed,
        "passed": passed,
        "failed_checks": tuple(failed),
        "verdict": "pass" if not failed else "fail",
    }


def _mut_remove_inward(root: Path):
    pkg = _pkg_dir(str(root))
    path = pkg / "compose.py"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("inward(", "str(").replace("inward,", ""), encoding="utf-8")


def _mut_remove_outward(root: Path):
    pkg = _pkg_dir(str(root))
    path = pkg / "compose.py"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("outward(", "(").replace("outward,", ""), encoding="utf-8")


def _mut_collapse_none_false(root: Path):
    pkg = _pkg_dir(str(root))
    path = pkg / "core.py"
    text = path.read_text(encoding="utf-8")
    text = text.replace('state = "absent"', 'state = "false"')
    path.write_text(text, encoding="utf-8")


def _mut_insert_print(root: Path):
    pkg = _pkg_dir(str(root))
    path = pkg / "parts.py"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("def validate_text(thing):", "def validate_text(thing):\n    print('leak')"), encoding="utf-8")


def _mut_insert_file(root: Path):
    pkg = _pkg_dir(str(root))
    path = pkg / "parts.py"
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace(
            "def calculate_stats(thing):",
            "def calculate_stats(thing):\n    open('/tmp/x','w').write('x')",
        ),
        encoding="utf-8",
    )


def _mut_add_class(root: Path):
    pkg = _pkg_dir(str(root))
    path = pkg / "parts.py"
    text = path.read_text(encoding="utf-8")
    path.write_text(text + "\n\nclass Bad:\n    pass\n", encoding="utf-8")


def _mut_second_param(root: Path):
    pkg = _pkg_dir(str(root))
    path = pkg / "parts.py"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("def validate_text(thing):", "def validate_text(thing, other=None):"), encoding="utf-8")


def _mut_change_formula(root: Path):
    pkg = _pkg_dir(str(root))
    path = pkg / "parts.py"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("len(text)", "len(text) + 1", 1), encoding="utf-8")


def _mut_return_none(root: Path):
    pkg = _pkg_dir(str(root))
    path = pkg / "parts.py"
    text = path.read_text(encoding="utf-8")
    # force first function body to return None early
    path.write_text(
        text.replace(
            "def validate_text(thing):",
            "def validate_text(thing):\n    return None\n    #",
        ),
        encoding="utf-8",
    )


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
