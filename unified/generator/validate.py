"""Validate a generator command thing (one input → one output)."""

from __future__ import annotations

from pathlib import Path

from ..thing import is_thing
from .names import is_valid_feature_name, is_valid_project_name, package_name_from_project


def validate(thing):
    """Check command shape and names; never write files."""
    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("validate:rejected-non-thing",),
            "state": "invalid",
        }

    value = thing["value"]
    if value is None:
        return {
            **thing,
            "evidence": (*thing["evidence"], "validate:absent-command"),
            "state": "absent",
        }
    if value is False:
        return {
            **thing,
            "evidence": (*thing["evidence"], "validate:false-command"),
            "state": "false",
        }
    if not isinstance(value, dict):
        return {
            **thing,
            "evidence": (*thing["evidence"], "validate:command-not-map"),
            "state": "invalid",
        }

    command = value.get("command")
    if command == "new":
        return _validate_new(thing, value)
    if command == "add":
        return _validate_add(thing, value)
    return {
        **thing,
        "evidence": (*thing["evidence"], f"validate:unknown-command:{command!r}"),
        "state": "invalid",
    }


def _validate_new(thing, value):
    name = value.get("name")
    if not is_valid_project_name(name):
        return {
            **thing,
            "evidence": (*thing["evidence"], "validate:invalid-project-name"),
            "state": "invalid",
        }

    parent = value.get("parent")
    if parent is None or parent is False:
        return {
            **thing,
            "evidence": (*thing["evidence"], "validate:missing-parent"),
            "state": "invalid",
        }
    if not isinstance(parent, str) or not parent:
        return {
            **thing,
            "evidence": (*thing["evidence"], "validate:invalid-parent"),
            "state": "invalid",
        }

    parent_path = Path(parent).expanduser().resolve()
    project_path = parent_path / name
    package = package_name_from_project(name)

    if project_path.exists():
        return {
            **thing,
            "value": {
                **value,
                "package": package,
                "project_path": str(project_path),
            },
            "evidence": (*thing["evidence"], "validate:project-exists"),
            "state": "invalid",
        }

    return {
        **thing,
        "value": {
            **value,
            "package": package,
            "project_path": str(project_path),
            "features": ("transform",),
        },
        "evidence": (*thing["evidence"], "validate:new-ok"),
        "state": "formed",
    }


def _validate_add(thing, value):
    name = value.get("name")
    if not is_valid_feature_name(name):
        return {
            **thing,
            "evidence": (*thing["evidence"], "validate:invalid-feature-name"),
            "state": "invalid",
        }

    root = value.get("project_root")
    if root is None:
        return {
            **thing,
            "evidence": (*thing["evidence"], "validate:absent-project-root"),
            "state": "absent",
        }
    if root is False:
        return {
            **thing,
            "evidence": (*thing["evidence"], "validate:false-project-root"),
            "state": "false",
        }
    if not isinstance(root, str) or not root:
        return {
            **thing,
            "evidence": (*thing["evidence"], "validate:invalid-project-root"),
            "state": "invalid",
        }

    project_root = Path(root).expanduser().resolve()
    pyproject = project_root / "pyproject.toml"
    if not pyproject.is_file():
        return {
            **thing,
            "evidence": (*thing["evidence"], "validate:not-a-project"),
            "state": "invalid",
        }

    meta = _read_project_meta(pyproject)
    if meta is None:
        return {
            **thing,
            "evidence": (*thing["evidence"], "validate:not-uc-generated"),
            "state": "invalid",
        }

    package = meta["package"]
    features_path = project_root / package / "features.py"
    if not features_path.is_file():
        return {
            **thing,
            "evidence": (*thing["evidence"], "validate:missing-features"),
            "state": "invalid",
        }

    features = _load_features(features_path)
    if features is None:
        return {
            **thing,
            "evidence": (*thing["evidence"], "validate:corrupt-features"),
            "state": "invalid",
        }

    if name in features:
        return {
            **thing,
            "value": {
                **value,
                "package": package,
                "project_path": str(project_root),
                "features": features,
            },
            "evidence": (*thing["evidence"], "validate:duplicate-feature"),
            "state": "invalid",
        }

    return {
        **thing,
        "value": {
            **value,
            "package": package,
            "project_path": str(project_root),
            "features": features,
            "feature": name,
        },
        "evidence": (*thing["evidence"], "validate:add-ok"),
        "state": "formed",
    }


def _read_project_meta(pyproject_path: Path):
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover
        import tomli as tomllib  # type: ignore

    try:
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None

    section = data.get("tool", {}).get("unified-code", {})
    if section.get("generated") is not True:
        return None
    package = section.get("package")
    if not isinstance(package, str) or not package.isidentifier():
        return None
    return {"package": package, "scale": section.get("scale", "UC-1")}


def _load_features(features_path: Path):
    text = features_path.read_text(encoding="utf-8")
    namespace: dict = {}
    try:
        exec(compile(text, str(features_path), "exec"), namespace, namespace)
    except Exception:
        return None
    features = namespace.get("FEATURES")
    if not isinstance(features, tuple):
        return None
    if any(not isinstance(item, str) for item in features):
        return None
    return features
