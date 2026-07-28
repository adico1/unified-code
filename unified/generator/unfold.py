"""uc unfold — seed → validated, generated, verified, installed application.

Atomicity:
  - build only under a temp directory
  - install to --output only after gates pass
  - on failure: keep diagnostics in temp, leave prior --output untouched
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from ..boundary import outward
from ..thing import is_thing
from .build import prepare_build
from .declaration import load_declaration_module
from .generate import generate
from .verify_plan import verify_plan
from .write_fs import write_project


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _tree_sha256(root: Path, exclude=frozenset()) -> str:
    """Deterministic content hash of a generated tree: sorted rel-path + file sha256."""
    root = Path(root)
    agg = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        if rel in exclude:
            continue
        agg.update(rel.encode("utf-8"))
        agg.update(b"\0")
        agg.update(hashlib.sha256(path.read_bytes()).hexdigest().encode("ascii"))
        agg.update(b"\n")
    return agg.hexdigest()


def _build_tree(prepared: dict, value: dict, tmp: str):
    """Run generate+write for a seed into an isolated temp parent. Thing→Thing."""
    built_input = {
        **prepared,
        "value": {
            **value,
            "parent": tmp,
            "project_name": value.get("project_name") or "app",
        },
    }
    return write_project(
        verify_plan(generate(prepare_build(load_declaration_module(built_input))))
    )


def prepare_unfold(thing):
    """Normalize host argv payload into a build-shaped thing + unfold flags."""
    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("prepare_unfold:rejected-non-thing",),
            "state": "invalid",
        }
    if thing["state"] in {"invalid", "absent", "false"}:
        return {
            **thing,
            "evidence": (*thing["evidence"], "prepare_unfold:skipped"),
            "state": thing["state"],
        }

    value = thing["value"]
    if not isinstance(value, dict):
        return {
            **thing,
            "evidence": (*thing["evidence"], "prepare_unfold:value-not-map"),
            "state": "invalid",
        }
    if value.get("error"):
        return {
            **thing,
            "evidence": (*thing["evidence"], f"prepare_unfold:{value.get('error')}"),
            "state": "invalid",
        }

    seed_path = value.get("seed_path") or value.get("declaration_path")
    if not seed_path or not isinstance(seed_path, str):
        return {
            **thing,
            "evidence": (*thing["evidence"], "prepare_unfold:missing-seed"),
            "state": "invalid",
        }

    seed = Path(seed_path).expanduser().resolve()
    if not seed.is_file():
        return {
            **thing,
            "evidence": (*thing["evidence"], "prepare_unfold:seed-not-found"),
            "state": "invalid",
        }

    output = value.get("output")
    if not output or not isinstance(output, str):
        return {
            **thing,
            "evidence": (*thing["evidence"], "prepare_unfold:missing-output"),
            "state": "invalid",
        }
    output_path = Path(output).expanduser().resolve()

    return {
        **thing,
        "value": {
            **value,
            "command": "build",
            "declaration_path": str(seed),
            "seed_path": str(seed),
            "output": str(output_path),
            "verify": bool(value.get("verify")),
            "run": bool(value.get("run")),
            "parent": None,  # filled after temp dir
            "project_name": value.get("project_name") or seed.stem,
        },
        "evidence": (*thing["evidence"], "prepare_unfold:ok"),
        "state": "formed",
    }


def _run_verify(project_path: Path) -> dict:
    """Run generated project tests when present. Returns {ok, detail}."""
    tests = project_path / "tests"
    if not tests.is_dir():
        return {"ok": True, "detail": "no-tests-dir", "exit": 0}
    configured_python = os.environ.get("UC_PYTHON")
    py = (
        Path(configured_python)
        if configured_python
        else _repo_root() / ".venv" / "bin" / "python"
    )
    if not py.is_file():
        py = Path("python3")
    try:
        r = subprocess.run(
            [str(py), "-m", "pytest", str(tests), "-q", "--tb=line"],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "detail": f"verify-exec:{exc}", "exit": -1}
    return {
        "ok": r.returncode == 0,
        "detail": (r.stdout or "")[-800:] + (r.stderr or "")[-400:],
        "exit": r.returncode,
    }


def _run_app(project_path: Path, seed_path: Path) -> dict:
    """Smoke-run generated CLI if package entry exists."""
    # Prefer python -m package if package dir exists
    pkgs = [
        p
        for p in project_path.iterdir()
        if p.is_dir() and (p / "__init__.py").is_file() and not p.name.startswith(".")
    ]
    py = _repo_root() / ".venv" / "bin" / "python"
    if not py.is_file():
        py = Path("python3")

    # Domain-neutral smoke: import package and call program if present
    if not pkgs:
        return {"ok": True, "detail": "no-package-to-run", "exit": 0}

    pkg = pkgs[0].name
    acceptance_path = project_path / ".uc" / "acceptance.json"
    if acceptance_path.is_file():
        try:
            acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
            commands = list(acceptance.get("commands") or ())
        except (OSError, ValueError) as exc:
            return {"ok": False, "detail": f"acceptance-read:{exc}", "exit": -1}
        outputs = []
        with tempfile.TemporaryDirectory(prefix="uc-app-run-") as run_tmp:
            state_path = Path(run_tmp) / "state.json"
            for index, case in enumerate(commands):
                argv = list(case.get("argv") or ())
                expected = case.get("expect")
                env = {
                    **__import__("os").environ,
                    "PYTHONPATH": str(project_path),
                }
                try:
                    result = subprocess.run(
                        [
                            str(py),
                            "-m",
                            pkg,
                            "--state",
                            str(state_path),
                            *argv,
                        ],
                        cwd=str(project_path),
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=120,
                        check=False,
                    )
                except (OSError, subprocess.TimeoutExpired) as exc:
                    return {
                        "ok": False,
                        "detail": f"acceptance-exec[{index}]:{exc}",
                        "exit": -1,
                    }
                try:
                    actual = json.loads((result.stdout or "").strip())
                except ValueError:
                    actual = {"invalid_stdout": (result.stdout or "").strip()}
                outputs.append(
                    {
                        "argv": argv,
                        "exit": result.returncode,
                        "output": actual,
                    }
                )
                if result.returncode != int(case.get("exit", 0)) or actual != expected:
                    return {
                        "ok": False,
                        "detail": json.dumps(outputs, ensure_ascii=False, sort_keys=True),
                        "exit": result.returncode,
                        "outputs": outputs,
                    }
        return {
            "ok": True,
            "detail": "\n".join(
                json.dumps(item["output"], ensure_ascii=False, separators=(",", ":"), sort_keys=True)
                for item in outputs
            ),
            "exit": 0,
            "outputs": outputs,
            "restart_verified": len(outputs) >= 2
            and outputs[-1]["output"] == outputs[-2]["output"],
            "seed": str(seed_path),
        }

    # Smoke: import package; if program() exists, call with minimal formed host.
    # Success = import + callable returns a Thing map (any state). Invalid state
    # from empty sample input still proves the app surface runs.
    script = f"""
import json, sys
sys.path.insert(0, {str(project_path)!r})
import {pkg} as app
if hasattr(app, "program") and callable(app.program):
    samples = [
        {{"source": "-", "text": "", "document": {{"items": []}}}},
        {{"source": "-", "text": "x", "document": {{"items": [{{"id": "1", "name": "x"}}]}}}},
        {{"source": "-", "text": "hello"}},
    ]
    last = None
    for val in samples:
        host = {{"value": val, "depths": (), "axes": (), "evidence": (), "state": "formed"}}
        try:
            out = app.program(host)
        except Exception as e:
            print(json.dumps({{"error": type(e).__name__, "msg": str(e)}}))
            sys.exit(1)
        if not isinstance(out, dict) or "state" not in out:
            print(json.dumps({{"error": "not-a-thing"}}))
            sys.exit(1)
        last = out
        if out.get("state") == "valid":
            print(json.dumps({{"state": "valid", "smoke": "ok"}}, sort_keys=True))
            sys.exit(0)
    print(json.dumps({{"state": last.get("state") if last else None, "smoke": "ran"}}, sort_keys=True))
    sys.exit(0)
print(json.dumps({{"imported": True, "package": {pkg!r}}}))
"""
    try:
        r = subprocess.run(
            [str(py), "-c", script],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "detail": f"run-exec:{exc}", "exit": -1}
    return {
        "ok": r.returncode == 0,
        "detail": ((r.stdout or "") + (r.stderr or ""))[-800:],
        "exit": r.returncode,
        "seed": str(seed_path),
    }


def _verify_python_c_application(seed_path: Path, app_outputs: list[dict]) -> dict:
    """Run every seed-declared transition independently in both UEM-16 hosts."""
    try:
        from unified.machine.bytecode import encode_program
        from unified.machine.canonical import canonical_bytes, canonical_sha256, from_python_run
        from unified.machine.host import run_compiled
        from unified.machine.l11 import run_c_vector
        from unified.machine.thing import blank_thing, value_of
        from unified.machine.validate import validate_symbolic

        declaration = json.loads(seed_path.read_text(encoding="utf-8"))
        feature = next(
            feature
            for feature in declaration.get("features") or ()
            if (feature.get("transformation") or {}).get("kind")
            == "stateful_resource"
        )
        transition = feature["transformation"]
        image = {
            "stateful": {"commands": transition["commands"]},
            "verify": {
                "require_value_field": "stats",
                "require_evidence_contains": [],
            },
        }
        symbolic = blank_thing(
            {
                "instructions": (
                    ("APPLY", "state_transition"),
                    ("VERIFY", "result"),
                    ("STOP", None),
                ),
                "image": image,
            }
        )
        compiled = encode_program(validate_symbolic(symbolic))
        if compiled.get("state") == "invalid":
            return {
                "ok": False,
                "detail": "compile-invalid",
                "evidence": list(compiled.get("evidence") or ()),
            }
        state = json.loads(json.dumps(transition["state"]["initial"]))
        cases = list(transition.get("acceptance") or ())
        if len(app_outputs) != len(cases):
            return {
                "ok": False,
                "detail": "application-output-count-mismatch",
                "expected": len(cases),
                "actual": len(app_outputs),
            }
        python_results = []
        c_results = []
        steps = []
        for index, (case, app_output) in enumerate(zip(cases, app_outputs)):
            argv = list(case.get("argv") or ())
            host = {
                "resource_state": state,
                "command": argv[0] if argv else None,
                "arguments": argv[1:],
            }
            python_result = from_python_run(
                compiled, run_compiled(compiled, host)
            )
            c_result, error = run_c_vector(compiled, host)
            if c_result is None:
                return {
                    "ok": False,
                    "detail": error or "c-host-unavailable",
                    "step": index,
                }
            equal = canonical_bytes(python_result) == canonical_bytes(c_result)
            envelope = python_result.get("stats") or {}
            expected_exit = int(case.get("exit", 0))
            expected_output = case.get("expect")
            if expected_exit == 0:
                application_equal = (
                    envelope.get("error") is None
                    and envelope.get("result") == expected_output
                    and app_output.get("exit") == expected_exit
                    and app_output.get("output") == expected_output
                )
                state = envelope.get("resource_state")
            else:
                application_equal = (
                    envelope.get("error") == expected_output.get("error")
                    and envelope.get("resource_state") == state
                    and envelope.get("state_changed") is False
                    and python_result.get("ticket") is None
                    and c_result.get("ticket") is None
                    and app_output.get("exit") == expected_exit
                    and app_output.get("output") == expected_output
                )
            steps.append(
                {
                    "argv": argv,
                    "equal": equal,
                    "application_equal": application_equal,
                    "state": python_result.get("state"),
                    "error": python_result.get("error"),
                    "python_sha256": canonical_sha256(python_result),
                    "c_sha256": canonical_sha256(c_result),
                }
            )
            python_results.append(python_result)
            c_results.append(c_result)
            if not equal or not application_equal:
                return {
                    "ok": False,
                    "equal": equal,
                    "application_equal": application_equal,
                    "detail": "transition-mismatch",
                    "step": index,
                    "steps": steps,
                    "python": python_result,
                    "c": c_result,
                }
        for rejection_index, case in enumerate(transition.get("rejections") or ()):
            argv = list(case.get("argv") or ())
            rejection_state = json.loads(
                json.dumps(transition["state"]["initial"])
            )
            host = {
                "resource_state": rejection_state,
                "command": argv[0] if argv else None,
                "arguments": argv[1:],
            }
            python_result = from_python_run(
                compiled, run_compiled(compiled, host)
            )
            c_result, error = run_c_vector(compiled, host)
            if c_result is None:
                return {
                    "ok": False,
                    "detail": error or "c-host-unavailable",
                    "rejection": rejection_index,
                }
            equal = canonical_bytes(python_result) == canonical_bytes(c_result)
            envelope = python_result.get("stats") or {}
            expected = case.get("expect") or {}
            application_equal = (
                envelope.get("error") == expected.get("error")
                and envelope.get("resource_state") == rejection_state
                and envelope.get("state_changed") is False
                and python_result.get("ticket") is None
                and c_result.get("ticket") is None
            )
            steps.append(
                {
                    "kind": "isolated-rejection",
                    "argv": argv,
                    "equal": equal,
                    "application_equal": application_equal,
                    "state": python_result.get("state"),
                    "error": python_result.get("error"),
                    "python_sha256": canonical_sha256(python_result),
                    "c_sha256": canonical_sha256(c_result),
                }
            )
            python_results.append(python_result)
            c_results.append(c_result)
            if not equal or not application_equal:
                return {
                    "ok": False,
                    "equal": equal,
                    "application_equal": application_equal,
                    "detail": "rejection-mismatch",
                    "rejection": rejection_index,
                    "steps": steps,
                    "python": python_result,
                    "c": c_result,
                }
        final_state_equal = state == transition["state"].get("expect")
        python_payload = json.loads(canonical_bytes({"steps": python_results}))
        c_payload = json.loads(canonical_bytes({"steps": c_results}))
        equal = canonical_bytes(python_payload) == canonical_bytes(c_payload)
        return {
            "ok": equal and final_state_equal,
            "equal": equal,
            "application_equal": True,
            "final_state_equal": final_state_equal,
            "python_sha256": canonical_sha256(python_payload),
            "c_sha256": canonical_sha256(c_payload),
            "program_sha256": value_of(compiled).get("program_sha256"),
            "steps": steps,
            "final_state": state,
        }
    except Exception as exc:  # noqa: BLE001 — verification boundary
        return {
            "ok": False,
            "detail": f"{type(exc).__name__}:{exc}",
        }


def install_atomic(thing):
    """After successful generate+write in temp, optionally verify/run then install."""
    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("install_atomic:rejected-non-thing",),
            "state": "invalid",
        }
    if thing["state"] != "valid":
        return {
            **thing,
            "evidence": (*thing["evidence"], "install_atomic:skipped-non-valid"),
            "state": thing["state"] if thing["state"] != "formed" else "invalid",
        }

    value = thing["value"]
    if not isinstance(value, dict):
        return {
            **thing,
            "evidence": (*thing["evidence"], "install_atomic:value-not-map"),
            "state": "invalid",
        }

    project_path = Path(value["project_path"])
    output = Path(value["output"])
    do_verify = bool(value.get("verify"))
    do_run = bool(value.get("run"))
    seed_path = Path(value.get("seed_path") or value.get("declaration_path") or ".")

    verify_result = {"ok": True, "detail": "verify-not-requested", "exit": 0}
    if do_verify:
        verify_result = _run_verify(project_path)
        if not verify_result["ok"]:
            return {
                **thing,
                "value": {
                    **value,
                    "verify_result": verify_result,
                    "install": "refused",
                    "temp_project": str(project_path),
                },
                "evidence": (
                    *thing["evidence"],
                    "install_atomic:verify-failed",
                    f"install_atomic:verify-exit:{verify_result.get('exit')}",
                ),
                "state": "invalid",
            }

    run_result = {"ok": True, "detail": "run-not-requested", "exit": 0}
    if do_run:
        run_result = _run_app(project_path, seed_path)
        if not run_result["ok"]:
            return {
                **thing,
                "value": {
                    **value,
                    "verify_result": verify_result,
                    "run_result": run_result,
                    "install": "refused",
                    "temp_project": str(project_path),
                },
                "evidence": (
                    *thing["evidence"],
                    "install_atomic:run-failed",
                    f"install_atomic:run-exit:{run_result.get('exit')}",
                ),
                "state": "invalid",
            }

    python_c_result = {"ok": True, "detail": "not-applicable"}
    outputs = run_result.get("outputs") if isinstance(run_result, dict) else None
    if do_verify and outputs:
        python_c_result = _verify_python_c_application(seed_path, outputs)
        if not python_c_result.get("ok"):
            return {
                **thing,
                "value": {
                    **value,
                    "verify_result": verify_result,
                    "run_result": run_result,
                    "python_c_result": python_c_result,
                    "install": "refused",
                    "temp_project": str(project_path),
                },
                "evidence": (
                    *thing["evidence"],
                    "install_atomic:python-c-failed",
                ),
                "state": "invalid",
            }

    # Atomic install: copy tree to staging beside output, then replace
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.parent / f".{output.name}.uc-staging"
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(
        project_path,
        staging,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
    )
    # write unfold manifest
    manifest = {
        "seed_path": str(seed_path),
        "output": str(output),
        "verify": do_verify,
        "run": do_run,
        "verify_result": {
            k: verify_result[k] for k in ("ok", "exit") if k in verify_result
        },
        "run_result": {k: run_result[k] for k in ("ok", "exit") if k in run_result},
        "python_c_result": python_c_result,
        "files": value.get("written") or value.get("files"),
    }
    (staging / ".uc" / "unfold_manifest.json").parent.mkdir(parents=True, exist_ok=True)
    (staging / ".uc" / "unfold_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    if output.exists():
        backup = output.parent / f".{output.name}.uc-prev"
        if backup.exists():
            shutil.rmtree(backup)
        output.rename(backup)
        try:
            staging.rename(output)
            shutil.rmtree(backup, ignore_errors=True)
        except OSError:
            # rollback
            if output.exists():
                shutil.rmtree(output, ignore_errors=True)
            if backup.exists():
                backup.rename(output)
            raise
    else:
        staging.rename(output)

    return {
        **thing,
        "value": {
            **value,
            "project_path": str(output),
            "temp_project": str(project_path),
            "install": "ok",
            "verify_result": verify_result,
            "run_result": run_result,
            "python_c_result": python_c_result,
            "unfold_manifest": str(output / ".uc" / "unfold_manifest.json"),
        },
        "evidence": (
            *thing["evidence"],
            "install_atomic:ok",
            f"install_atomic:path:{output}",
        ),
        "state": "valid",
    }


def run_unfold(thing):
    """Full unfold pipeline. One thing in, one thing out."""
    prepared = prepare_unfold(thing)
    if prepared.get("state") != "formed":
        return outward(prepared)

    value = prepared["value"]
    # --verify includes deterministic rebuild verification.  --fixed-point is
    # retained as an explicit alias for older automation.
    do_fixed_point = bool(value.get("fixed_point") or value.get("verify"))
    do_clean_room = bool(value.get("clean_room"))
    tmp = tempfile.mkdtemp(prefix="uc-unfold-")
    try:
        written = _build_tree(prepared, value, tmp)
        wval = written["value"] if isinstance(written.get("value"), dict) else {}
        proj = wval.get("project_path")

        fixed_point = None
        if do_fixed_point and written.get("state") == "valid" and proj:
            tree_a = _tree_sha256(Path(proj))
            tmp2 = tempfile.mkdtemp(prefix="uc-unfold-fp-")
            try:
                written2 = _build_tree(prepared, value, tmp2)
                w2 = written2["value"] if isinstance(written2.get("value"), dict) else {}
                proj2 = w2.get("project_path")
                tree_b = _tree_sha256(Path(proj2)) if proj2 else ""
            finally:
                shutil.rmtree(tmp2, ignore_errors=True)
            match = bool(tree_a) and tree_a == tree_b
            fixed_point = {
                "ok": match,
                "match": match,
                "tree_sha256_a": tree_a,
                "tree_sha256_b": tree_b,
                "scope": "application-tree",
            }
            if not match:
                return outward(
                    {
                        **written,
                        "value": {
                            **wval,
                            "fixed_point": fixed_point,
                            "install": "refused",
                        },
                        "evidence": (
                            *written.get("evidence", ()),
                            "unfold:fixed-point-mismatch",
                        ),
                        "state": "invalid",
                    }
                )

        clean_room = None
        if do_clean_room:
            # The generated app tree is built only in an isolated temp parent from
            # the seed; no repo files are copied into it. This is application-tree
            # clean-room. The full-tree framework clean-room (Stage0+ROOT.seed →
            # whole repository) is a separate, still-open standard-ten gap.
            clean_room = {
                "ok": True,
                "scope": "application-tree",
                "temp_parent": tmp,
                "note": "generated app tree built from seed only; no repo copy",
                "full_tree_framework": "gap.clean-room-full-tree (not claimed here)",
            }

        if fixed_point or clean_room:
            extra = {}
            if fixed_point:
                extra["fixed_point"] = fixed_point
            if clean_room:
                extra["clean_room"] = clean_room
            written = {**written, "value": {**wval, **extra}}

        installed = install_atomic(written)
        return outward(installed)
    except Exception as exc:  # noqa: BLE001 — host boundary records fault
        return outward(
            {
                **prepared,
                "value": {
                    **value,
                    "error": "unfold-exception",
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                    "temp_dir": tmp,
                },
                "evidence": (
                    *prepared.get("evidence", ()),
                    "unfold:exception",
                    f"unfold:error_type:{type(exc).__name__}",
                ),
                "state": "invalid",
            }
        )
