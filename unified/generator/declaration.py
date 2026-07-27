"""Code-based declarations as Unified Code parts.

Preferred form (one thing in, one thing out):

    def declaration(thing):
        return {**thing, "value": {...plain program data...}}

Module loading is a named authority boundary (load_declaration_module).
No unrestricted eval of feature logic. No YAML/JSON config as source of truth.
"""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
from typing import Any


def _python_declarations_allowed(value: dict) -> bool:
    """Executable Python declarations are legacy compatibility fixtures only.

    Canonical JSON is the sole authoritative declaration input. Loading a
    host-code (.py) declaration is denied unless explicitly opted in, either
    per-call (``allow_python_declaration`` in the thing value) or process-wide
    (``UC_ALLOW_PY_DECLARATIONS=1``). Clean-room and fixed-point proofs leave
    both unset, so no host-code declaration can reach the build path, and there
    is never a JSON→Python fallback (dispatch is purely by file suffix).
    """
    if isinstance(value, dict) and value.get("allow_python_declaration"):
        return True
    return os.environ.get("UC_ALLOW_PY_DECLARATIONS") == "1"

from ..thing import is_thing
from . import expr as _expr
from .names import is_valid_feature_name, is_valid_project_name, package_name_from_project

# op -> canonical expression builder (same constructors the .py declarations use)
_EXPR_BUILDERS = {
    "literal": _expr.literal,
    "field": _expr.field,
    "ref": _expr.ref,
    "object": _expr.object_expr,
    "count": _expr.count,
    "as_int": _expr.as_int,
    "as_decimal": _expr.as_decimal,
    "require": _expr.require,
    "min_value": _expr.min_value,
    "max_value": _expr.max_value,
    "mul": _expr.mul,
    "add": _expr.add,
    "sum_each": _expr.sum_each,
    "quantize": _expr.quantize,
    "decimal_str": _expr.decimal_str,
    "str_len": _expr.str_len,
    "line_count": _expr.line_count,
    "word_count": _expr.word_count,
    "unique_casefold_word_count": _expr.unique_casefold_word_count,
}


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

    # Canonical declarative seed data (Standard Ten rule 4): a .json declaration
    # carries generic expression trees / events / routes / boundaries as pure
    # data — no executable host-language code. Same downstream normalization.
    if file_path.suffix == ".json":
        return _load_json_declaration(thing, value, file_path)

    # Any non-JSON declaration is executable host code (legacy). Denied unless
    # explicitly opted in — canonical JSON is the sole authoritative input.
    if not _python_declarations_allowed(value):
        return {
            **thing,
            "value": {
                **value,
                "error": "python-declaration-denied",
                "declaration_path": str(file_path),
            },
            "evidence": (
                *thing["evidence"],
                "boundary:load_declaration_module",
                "load:python-declaration-denied",
            ),
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


def _normalize_expr_node(node):
    """Canonicalize a JSON expression node to exact .py-builder shape.

    Two things differ between a hand-authored JSON node and a builder-emitted
    one: JSON has no tuple type (the validator requires tuple ``path``), and JSON
    preserves the source file's key order while generated code serializes nodes
    via ``repr`` (key-order sensitive). Routing each node through the same
    ``expr.py`` constructor the .py declarations use is the single authoritative
    source for both — so a .json and an equivalent .py declaration yield
    byte-identical generated output. Children are normalized first, then the
    parent, so nested nodes reach the builder already canonical.
    """
    if not isinstance(node, dict) or "op" not in node:
        return node
    op = node["op"]
    cfg = {}
    for key, val in node.items():
        if key == "op":
            continue
        if isinstance(val, dict) and "op" in val:
            cfg[key] = _normalize_expr_node(val)
        elif isinstance(val, list) and val and all(
            isinstance(x, dict) and "op" in x for x in val
        ):
            cfg[key] = [_normalize_expr_node(x) for x in val]
        elif key == "fields" and isinstance(val, dict):
            cfg[key] = {k: _normalize_expr_node(v) for k, v in val.items()}
        else:
            cfg[key] = val
    builder = _EXPR_BUILDERS.get(op)
    if builder is None:
        return {"op": op, **cfg}
    built = builder(cfg)
    result = built.get("value") if isinstance(built, dict) else None
    if built.get("state") == "formed" and isinstance(result, dict):
        return result
    return {"op": op, **cfg}


def _normalize_transformation(transformation: dict) -> dict:
    """Canonicalize every expression node a transformation carries.

    Expression nodes appear in three places: ``program`` (or its ``result``
    alias) and each value of the ``bindings`` (CSE) map. Each is routed through
    the builder canonicalizer so JSON key order inside a node cannot affect
    generated bytes. The ``bindings`` map's own key order and object ``fields``
    order are preserved: they are semantic (bindings evaluate sequentially so
    later ones may ``ref`` earlier ones; ``fields`` fixes output order), not
    representational.
    """
    out = dict(transformation)
    for key in ("program", "result"):
        node = out.get(key)
        if isinstance(node, dict) and "op" in node:
            out[key] = _normalize_expr_node(node)
    bindings = out.get("bindings")
    if isinstance(bindings, dict):
        out["bindings"] = {
            name: (_normalize_expr_node(node) if isinstance(node, dict) and "op" in node else node)
            for name, node in bindings.items()
        }
    return out


def _normalize_json_exprs(raw: dict) -> dict:
    """Canonicalize expression nodes in every feature transformation."""

    def fix_feature(feat):
        if not isinstance(feat, dict):
            return feat
        transformation = feat.get("transformation")
        if isinstance(transformation, dict):
            feat = {**feat, "transformation": _normalize_transformation(transformation)}
        return feat

    if isinstance(raw.get("features"), list):
        return {**raw, "features": [fix_feature(f) for f in raw["features"]]}
    if isinstance(raw.get("transformation"), dict):  # feature-kind declaration
        return fix_feature(raw)
    return raw


def _load_json_declaration(thing, value, file_path: Path):
    """Load a pure-JSON declaration (no executable host code) and normalize it.

    Mirrors the module path's normalization tail so a .json and an equivalent
    .py declaration produce byte-identical downstream declarations.
    """
    ev = (*thing["evidence"], "boundary:load_declaration_module", "load:json")
    try:
        raw = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {
            **thing,
            "value": {**value, "error": "declaration-parse-failed", "detail": str(exc)},
            "evidence": (*ev, "load:parse-failed"),
            "state": "invalid",
        }
    if not isinstance(raw, dict):
        return {
            **thing,
            "value": {**value, "error": "declaration-not-map"},
            "evidence": (*ev, "load:not-map"),
            "state": "invalid",
        }

    # Canonicalize expression nodes (JSON lists → builder tuples) so validation
    # and generated output match the equivalent .py declaration exactly.
    raw = _normalize_json_exprs(raw)

    # Kind from data shape: a feature carries role/transformation and no features list.
    if "features" not in raw and ("transformation" in raw or "role" in raw):
        kind = "feature"
    else:
        kind = "program"

    if "project" in raw and "features" in raw:
        program_raw = _from_nested_value(raw)
    else:
        program_raw = raw

    normalized = normalize_feature(program_raw) if kind == "feature" else normalize_program(program_raw)
    if not normalized.get("ok"):
        return {
            **thing,
            "value": {**value, "error": normalized.get("error"), "declaration_path": str(file_path)},
            "evidence": (*ev, "load:normalize-failed", f"load:{normalized.get('error')}"),
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
        "evidence": (*ev, "load:ok", f"load:kind:{kind}"),
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
