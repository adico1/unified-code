"""Code-based declarations as Unified Code parts.

Preferred form (one thing in, one thing out):

    def declaration(thing):
        return {**thing, "value": {...plain program data...}}

Module loading is a named authority boundary (load_declaration_module).
No unrestricted eval of feature logic. No YAML/JSON config as source of truth.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from ..thing import is_thing
from .names import is_valid_feature_name, is_valid_project_name, package_name_from_project


def load_declaration_module(thing):
    """Named boundary: load a declaration module path from thing["value"].

    Authority: executes the module namespace only to bind ``declaration``
    (callable) or ``PROGRAM``/``FEATURE`` (plain dict). Recorded in evidence.
    """
    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("boundary:load_declaration_module", "load:rejected-non-thing"),
            "state": "invalid",
        }

    value = thing["value"]
    if not isinstance(value, dict):
        return {
            **thing,
            "evidence": (*thing["evidence"], "boundary:load_declaration_module", "load:value-not-map"),
            "state": "invalid",
        }

    path = value.get("declaration_path") or value.get("path")
    if path is None:
        return {
            **thing,
            "evidence": (*thing["evidence"], "boundary:load_declaration_module", "load:absent-path"),
            "state": "absent",
        }
    if path is False:
        return {
            **thing,
            "evidence": (*thing["evidence"], "boundary:load_declaration_module", "load:false-path"),
            "state": "false",
        }
    if not isinstance(path, str) or not path:
        return {
            **thing,
            "evidence": (*thing["evidence"], "boundary:load_declaration_module", "load:invalid-path"),
            "state": "invalid",
        }

    file_path = Path(path).expanduser().resolve()
    if not file_path.is_file():
        return {
            **thing,
            "value": {**value, "error": "declaration-not-found", "declaration_path": str(file_path)},
            "evidence": (*thing["evidence"], "boundary:load_declaration_module", "load:not-found"),
            "state": "invalid",
        }

    # Static hygiene: refuse modules that define classes (L8 at declaration source).
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (OSError, SyntaxError) as exc:
        return {
            **thing,
            "value": {**value, "error": "declaration-parse-failed", "detail": str(exc)},
            "evidence": (*thing["evidence"], "boundary:load_declaration_module", "load:parse-failed"),
            "state": "invalid",
        }

    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef)):
            return {
                **thing,
                "value": {**value, "error": "declaration-has-class-or-async"},
                "evidence": (*thing["evidence"], "boundary:load_declaration_module", "load:rejected-shape"),
                "state": "invalid",
            }

    namespace: dict[str, Any] = {"__name__": "uc_declaration"}
    try:
        # Named authority boundary — module execution is explicit and evidenced.
        exec(compile(source, str(file_path), "exec"), namespace, namespace)
    except Exception as exc:  # noqa: BLE001
        return {
            **thing,
            "value": {
                **value,
                "error": "declaration-exec-failed",
                "detail": f"{type(exc).__name__}:{exc}",
            },
            "evidence": (*thing["evidence"], "boundary:load_declaration_module", "load:exec-failed"),
            "state": "invalid",
        }

    raw = None
    kind = None
    if callable(namespace.get("declaration")):
        # Run declaration(thing) as a Part — one in, one out.
        admitted = {
            "value": {},
            "depths": (),
            "axes": (),
            "evidence": ("declaration:invoke",),
            "state": "unknown",
        }
        try:
            produced = namespace["declaration"](admitted)
        except Exception as exc:  # noqa: BLE001
            return {
                **thing,
                "value": {**value, "error": "declaration-call-failed", "detail": str(exc)},
                "evidence": (*thing["evidence"], "boundary:load_declaration_module", "load:call-failed"),
                "state": "invalid",
            }
        if not is_thing(produced):
            return {
                **thing,
                "value": {**value, "error": "declaration-returned-non-thing"},
                "evidence": (*thing["evidence"], "boundary:load_declaration_module", "load:non-thing"),
                "state": "invalid",
            }
        raw = produced.get("value")
        kind = "program"
    elif "PROGRAM" in namespace:
        raw = namespace["PROGRAM"]
        kind = "program"
    elif "FEATURE" in namespace:
        raw = namespace["FEATURE"]
        kind = "feature"
    else:
        return {
            **thing,
            "value": {**value, "error": "declaration-missing-entry"},
            "evidence": (*thing["evidence"], "boundary:load_declaration_module", "load:missing-entry"),
            "state": "invalid",
        }

    if not isinstance(raw, dict):
        return {
            **thing,
            "value": {**value, "error": "declaration-not-map"},
            "evidence": (*thing["evidence"], "boundary:load_declaration_module", "load:not-map"),
            "state": "invalid",
        }

    # Support both flat PROGRAM and nested value form from declaration(thing).
    if "project" in raw and "features" in raw:
        program_raw = _from_nested_value(raw)
    else:
        program_raw = raw

    if kind == "feature":
        normalized = normalize_feature(program_raw)
    else:
        normalized = normalize_program(program_raw)

    if not normalized.get("ok"):
        return {
            **thing,
            "value": {**value, "error": normalized.get("error"), "declaration_path": str(file_path)},
            "evidence": (
                *thing["evidence"],
                "boundary:load_declaration_module",
                "load:normalize-failed",
                f"load:{normalized.get('error')}",
            ),
            "state": "invalid",
        }

    return {
        **thing,
        "value": {
            **value,
            "declaration_path": str(file_path),
            "kind": kind,
            "declaration": normalized["declaration"],
        },
        "evidence": (
            *thing["evidence"],
            "boundary:load_declaration_module",
            "load:ok",
            f"load:kind:{kind}",
        ),
        "state": "formed",
    }


# Back-compat alias used by older validate paths.
def load_declaration_file(path: str | Path) -> dict[str, Any]:
    thing = {
        "value": {"declaration_path": str(path)},
        "depths": (),
        "axes": (),
        "evidence": (),
        "state": "unknown",
    }
    loaded = load_declaration_module(thing)
    if loaded["state"] != "formed":
        return {
            "ok": False,
            "error": (loaded.get("value") or {}).get("error", "load-failed"),
            "path": str(path),
        }
    return {
        "ok": True,
        "kind": loaded["value"]["kind"],
        "declaration": loaded["value"]["declaration"],
        "path": str(path),
    }


def _from_nested_value(raw: dict) -> dict:
    """Map declaration(thing) value layout to PROGRAM layout."""
    project = raw.get("project") or {}
    if isinstance(project, str):
        project = {"name": project}
    name = project.get("name") or raw.get("name")
    package = project.get("package") or package_name_from_project(name) if isinstance(name, str) else raw.get("package")
    return {
        "name": name,
        "package": package,
        "description": project.get("description") or raw.get("description", ""),
        "composition": raw.get("composition"),
        "boundaries": raw.get("boundaries", ()),
        "cli": raw.get("cli") or raw.get("inputs", {}).get("cli"),
        "presentation": raw.get("presentation"),
        "verify": raw.get("verify") or raw.get("invariants", {}).get("verify") if isinstance(raw.get("invariants"), dict) else raw.get("verify"),
        "features": raw.get("features", ()),
        "tests": raw.get("tests", ()),
        "inputs": raw.get("inputs"),
        "errors": raw.get("errors"),
        "invariants": raw.get("invariants") if not isinstance(raw.get("invariants"), dict) else raw.get("invariants"),
    }


def normalize_feature(raw: dict) -> dict[str, Any]:
    name = raw.get("name")
    if not is_valid_feature_name(name):
        return {"ok": False, "error": "declaration-invalid-feature-name"}

    role = raw.get("role", "transform")
    if role not in {"transform", "validate", "identity"}:
        return {"ok": False, "error": "declaration-invalid-role"}

    transformation = raw.get("transformation") or {}
    if not isinstance(transformation, dict):
        return {"ok": False, "error": "declaration-transformation-not-map"}

    input_shape = raw.get("input_shape") or {"type": "any"}
    if not isinstance(input_shape, dict):
        return {"ok": False, "error": "declaration-input-shape-not-map"}

    def _tup(key, default=()):
        val = raw.get(key, default)
        if isinstance(val, list):
            val = tuple(val)
        if not isinstance(val, tuple):
            return None
        return val

    for key in ("invariants", "errors", "tests", "boundaries"):
        if _tup(key) is None and key in raw:
            return {"ok": False, "error": f"declaration-{key}-not-sequence"}

    return {
        "ok": True,
        "declaration": {
            "name": name,
            "role": role,
            "input_shape": input_shape,
            "transformation": transformation,
            "invariants": _tup("invariants") or (),
            "errors": _tup("errors") or (),
            "boundaries": _tup("boundaries") or (),
            "tests": _tup("tests") or (),
            "doc": raw.get("doc", f"Declared feature {name}."),
        },
    }


def normalize_program(raw: dict) -> dict[str, Any]:
    name = raw.get("name")
    if not isinstance(name, str) or not name:
        return {"ok": False, "error": "declaration-invalid-program-name"}
    # Project directory name may use hyphens; package is separate.
    package = raw.get("package")
    if not isinstance(package, str) or not package.isidentifier():
        if is_valid_project_name(name):
            package = package_name_from_project(name)
        else:
            return {"ok": False, "error": "declaration-invalid-package"}

    features_raw = raw.get("features", ())
    if isinstance(features_raw, list):
        features_raw = tuple(features_raw)
    if not isinstance(features_raw, tuple) or not features_raw:
        return {"ok": False, "error": "declaration-features-required"}

    features = []
    for item in features_raw:
        if not isinstance(item, dict):
            return {"ok": False, "error": "declaration-feature-not-map"}
        norm = normalize_feature(item)
        if not norm.get("ok"):
            return norm
        features.append(norm["declaration"])

    composition = raw.get("composition")
    if composition is None:
        composition = (
            "inward",
            "letter",
            *tuple(f["name"] for f in features),
            "verify",
            "outward",
        )
    if isinstance(composition, list):
        composition = tuple(composition)
    if not isinstance(composition, tuple) or not composition:
        return {"ok": False, "error": "declaration-composition-invalid"}

    # Reject forced identity transform when not declared as a feature.
    feature_names = {f["name"] for f in features}
    if "transform" in composition and "transform" not in feature_names:
        composition = tuple(step for step in composition if step != "transform")

    boundaries = raw.get("boundaries", ())
    if isinstance(boundaries, list):
        boundaries = tuple(boundaries)
    if not isinstance(boundaries, tuple):
        return {"ok": False, "error": "declaration-boundaries-not-sequence"}

    cli = raw.get("cli")
    if cli is not None and not isinstance(cli, dict):
        return {"ok": False, "error": "declaration-cli-not-map"}

    # Derive CLI from inputs if provided.
    inputs = raw.get("inputs")
    if cli is None and isinstance(inputs, dict) and "cli" in inputs:
        cli = inputs["cli"]

    presentation = raw.get("presentation")
    if presentation is not None and not isinstance(presentation, dict):
        return {"ok": False, "error": "declaration-presentation-not-map"}

    verify = raw.get("verify")
    if verify is not None and not isinstance(verify, dict):
        return {"ok": False, "error": "declaration-verify-not-map"}

    tests = raw.get("tests", ())
    if isinstance(tests, list):
        tests = tuple(tests)
    if not isinstance(tests, tuple):
        return {"ok": False, "error": "declaration-tests-not-sequence"}

    return {
        "ok": True,
        "declaration": {
            "name": name,
            "package": package,
            "description": raw.get("description") or "Unified Code generated program",
            "features": tuple(features),
            "composition": composition,
            "boundaries": boundaries,
            "cli": cli,
            "presentation": presentation,
            "verify": verify,
            "tests": tests,
            "errors": raw.get("errors") or (),
            "inputs": inputs,
        },
    }
