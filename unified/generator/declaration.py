"""Load and normalize code-based feature/program declarations (plain data).

A declaration file is Python that defines ``FEATURE`` or ``PROGRAM`` as a
dict. No YAML. No classes. Loading only reads data; it does not execute
feature logic beyond defining the dict.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .names import is_valid_feature_name, is_valid_project_name


def load_declaration_file(path: str | Path) -> dict[str, Any]:
    """Load FEATURE or PROGRAM from a .py file into a plain dict."""
    file_path = Path(path).expanduser().resolve()
    if not file_path.is_file():
        return {"ok": False, "error": "declaration-not-found", "path": str(file_path)}
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError:
        return {"ok": False, "error": "declaration-unreadable", "path": str(file_path)}

    namespace: dict[str, Any] = {}
    try:
        exec(compile(text, str(file_path), "exec"), namespace, namespace)
    except Exception as exc:  # noqa: BLE001 — surface as invalid declaration
        return {
            "ok": False,
            "error": "declaration-exec-failed",
            "detail": f"{type(exc).__name__}:{exc}",
            "path": str(file_path),
        }

    if "PROGRAM" in namespace:
        raw = namespace["PROGRAM"]
        kind = "program"
    elif "FEATURE" in namespace:
        raw = namespace["FEATURE"]
        kind = "feature"
    else:
        return {
            "ok": False,
            "error": "declaration-missing-FEATURE-or-PROGRAM",
            "path": str(file_path),
        }

    if not isinstance(raw, dict):
        return {"ok": False, "error": "declaration-not-map", "path": str(file_path)}

    if kind == "feature":
        normalized = normalize_feature(raw)
    else:
        normalized = normalize_program(raw)

    if not normalized.get("ok"):
        return {**normalized, "path": str(file_path)}
    return {
        "ok": True,
        "kind": kind,
        "declaration": normalized["declaration"],
        "path": str(file_path),
    }


def normalize_feature(raw: dict) -> dict[str, Any]:
    name = raw.get("name")
    if not is_valid_feature_name(name):
        return {"ok": False, "error": "declaration-invalid-feature-name"}

    role = raw.get("role", "transform")
    if role not in {"transform", "validate", "identity"}:
        return {"ok": False, "error": "declaration-invalid-role"}

    transformation = raw.get("transformation", {})
    if transformation is None:
        transformation = {}
    if not isinstance(transformation, dict):
        return {"ok": False, "error": "declaration-transformation-not-map"}

    input_shape = raw.get("input_shape", {"type": "any"})
    if not isinstance(input_shape, dict):
        return {"ok": False, "error": "declaration-input-shape-not-map"}

    invariants = raw.get("invariants", ())
    if isinstance(invariants, list):
        invariants = tuple(invariants)
    if not isinstance(invariants, tuple):
        return {"ok": False, "error": "declaration-invariants-not-sequence"}

    errors = raw.get("errors", ())
    if isinstance(errors, list):
        errors = tuple(errors)
    if not isinstance(errors, tuple):
        return {"ok": False, "error": "declaration-errors-not-sequence"}

    tests = raw.get("tests", ())
    if isinstance(tests, list):
        tests = tuple(tests)
    if not isinstance(tests, tuple):
        return {"ok": False, "error": "declaration-tests-not-sequence"}

    boundaries = raw.get("boundaries", ())
    if isinstance(boundaries, list):
        boundaries = tuple(boundaries)
    if not isinstance(boundaries, tuple):
        return {"ok": False, "error": "declaration-boundaries-not-sequence"}

    return {
        "ok": True,
        "declaration": {
            "name": name,
            "role": role,
            "input_shape": input_shape,
            "transformation": transformation,
            "invariants": invariants,
            "errors": errors,
            "boundaries": boundaries,
            "tests": tests,
            "doc": raw.get("doc", f"Declared feature {name}."),
        },
    }


def normalize_program(raw: dict) -> dict[str, Any]:
    name = raw.get("name")
    if not is_valid_project_name(name) if isinstance(name, str) else False:
        # allow underscores in package-style names that map from project names
        if not isinstance(name, str) or not name:
            return {"ok": False, "error": "declaration-invalid-program-name"}

    package = raw.get("package")
    if not isinstance(package, str) or not package.isidentifier():
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

    boundaries = raw.get("boundaries", ())
    if isinstance(boundaries, list):
        boundaries = tuple(boundaries)
    if not isinstance(boundaries, tuple):
        return {"ok": False, "error": "declaration-boundaries-not-sequence"}

    cli = raw.get("cli")
    if cli is not None and not isinstance(cli, dict):
        return {"ok": False, "error": "declaration-cli-not-map"}

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
            "description": raw.get("description", "Unified Code generated program"),
            "features": tuple(features),
            "composition": composition,
            "boundaries": boundaries,
            "cli": cli,
            "presentation": presentation,
            "verify": verify,
            "tests": tests,
        },
    }
