"""Application-vocabulary derivation and generic-source intersection checks."""

from __future__ import annotations

import json
import re
from pathlib import Path


GENERIC_SCHEMA_ALLOWLIST = frozenset(
    {
        "acceptance",
        "actions",
        "add",
        "append",
        "arg",
        "arguments",
        "array",
        "as",
        "boolean",
        "command",
        "commands",
        "default",
        "default_path",
        "duplicate",
        "equals",
        "error",
        "expect",
        "failure_probe",
        "field",
        "fields",
        "formed",
        "guards",
        "increment",
        "initial",
        "integer",
        "invalid",
        "invalid-argument",
        "invalid-arity",
        "kind",
        "literal",
        "minimum",
        "name",
        "non_empty",
        "object",
        "open",
        "path",
        "persistence",
        "project",
        "rejections",
        "require",
        "resource_state",
        "result",
        "schema",
        "selected",
        "set",
        "state",
        "state_changed",
        "stateful_resource",
        "string",
        "target",
        "type",
        "unique",
        "unknown",
        "unknown-command",
        "value",
        "values",
        "where",
    }
)


def _add(vocabulary, value, mode="token", components=False):
    if not isinstance(value, str):
        return
    term = value.lower()
    if term and term not in GENERIC_SCHEMA_ALLOWLIST:
        if term not in vocabulary or mode == "token":
            vocabulary[term] = mode
    if components:
        for component in re.split(r"[-_]", term):
            if len(component) >= 4 and component not in GENERIC_SCHEMA_ALLOWLIST:
                vocabulary[component] = "token"


def _collect_command_vocabulary(value, vocabulary):
    if isinstance(value, dict):
        for key, nested in value.items():
            if not key.startswith("$") and key not in GENERIC_SCHEMA_ALLOWLIST:
                _add(vocabulary, key, mode="literal")
            if key in {"error", "field", "as", "target", "name"}:
                _add(vocabulary, nested, components=key == "error")
            elif key in {"path", "fields"} and isinstance(nested, list):
                for item in nested:
                    _add(vocabulary, item)
            _collect_command_vocabulary(nested, vocabulary)
    elif isinstance(value, list):
        for nested in value:
            _collect_command_vocabulary(nested, vocabulary)


def derive_application_vocabulary(seed_paths) -> dict[str, str]:
    """Return term → matching mode, derived from every proof declaration."""
    vocabulary: dict[str, str] = {}
    for path in seed_paths:
        declaration = json.loads(Path(path).read_text(encoding="utf-8"))
        _add(vocabulary, declaration.get("name"))
        _add(vocabulary, declaration.get("package"))
        for feature in declaration.get("features") or ():
            transformation = feature.get("transformation") or {}
            if transformation.get("kind") != "stateful_resource":
                continue
            _add(vocabulary, feature.get("name"))
            for error in feature.get("errors") or ():
                _add(vocabulary, error, components=True)
            for command in (transformation.get("commands") or {}):
                if command.lower() not in GENERIC_SCHEMA_ALLOWLIST:
                    vocabulary[command.lower()] = "literal"
            _collect_command_vocabulary(
                transformation.get("commands") or {}, vocabulary
            )
            _collect_command_vocabulary(
                (transformation.get("state") or {}).get("initial") or {},
                vocabulary,
            )
            persistence = transformation.get("persistence") or {}
            _add(vocabulary, persistence.get("environment"))
            _add(vocabulary, persistence.get("default_path"))
    return dict(sorted(vocabulary.items()))


def _matches(text: str, term: str, mode: str) -> bool:
    if mode == "literal":
        return bool(
            re.search(
                rf"(?P<quote>['\"]){re.escape(term)}(?P=quote)",
                text,
                flags=re.IGNORECASE,
            )
        )
    return bool(
        re.search(
            rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])",
            text,
            flags=re.IGNORECASE,
        )
    )


def _without_comments(path: Path, text: str) -> str:
    if path.suffix == ".py":
        return re.sub(r"(?m)#.*$", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"(?m)//.*$", "", text)


def vocabulary_hits(roots, seed_paths, display_root=None) -> list[tuple[str, str]]:
    """Return every proof-seed term found in the selected generic source roots."""
    vocabulary = derive_application_vocabulary(seed_paths)
    display_root = Path(display_root).resolve() if display_root else None
    hits = []
    for root in (Path(item) for item in roots):
        paths = (root,) if root.is_file() else root.rglob("*")
        for path in paths:
            if not path.is_file() or path.suffix not in {".py", ".c", ".h"}:
                continue
            text = _without_comments(
                path, path.read_text(encoding="utf-8")
            ).lower()
            for term, mode in vocabulary.items():
                if _matches(text, term, mode):
                    display = str(path)
                    if display_root:
                        try:
                            display = str(path.resolve().relative_to(display_root))
                        except ValueError:
                            pass
                    hits.append((display, term))
    return sorted(set(hits))
