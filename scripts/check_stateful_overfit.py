#!/usr/bin/env python3
"""Prove proof-seed application vocabulary is absent from generic source."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROOF_SEEDS = (
    ROOT / "seed" / "declarations" / "task_ledger.json",
    ROOT / "seed" / "declarations" / "score_board.json",
)
GENERIC_ROOTS = (
    ROOT / "unified" / "generator",
    ROOT / "unified" / "machine",
    ROOT / "c" / "core",
)

# These strings define the generic declaration/UEM language. A proof seed may
# use them without turning them into application vocabulary.
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
        "commands",
        "default",
        "default_path",
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
        "unknown-command",
        "value",
        "values",
        "where",
    }
)


def _add(vocabulary, value, mode="token", singular=False):
    if not isinstance(value, str):
        return
    term = value.lower()
    if term and term not in GENERIC_SCHEMA_ALLOWLIST:
        if term not in vocabulary or mode == "token":
            vocabulary[term] = mode
    if singular and term in {"players", "tasks"}:
        vocabulary.setdefault(term[:-1], mode)


def _collect_command_vocabulary(value, vocabulary):
    if isinstance(value, dict):
        for key, nested in value.items():
            if not key.startswith("$") and key not in GENERIC_SCHEMA_ALLOWLIST:
                _add(vocabulary, key, mode="literal", singular=True)
            if key in {"error", "field", "as", "target", "name"}:
                _add(vocabulary, nested, singular=True)
            elif key in {"path", "fields"} and isinstance(nested, list):
                for item in nested:
                    _add(vocabulary, item, singular=True)
            _collect_command_vocabulary(nested, vocabulary)
    elif isinstance(value, list):
        for nested in value:
            _collect_command_vocabulary(nested, vocabulary)


def derive_application_vocabulary(seed_paths=PROOF_SEEDS) -> dict[str, str]:
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
                _add(vocabulary, error)
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


def vocabulary_hits(
    roots=GENERIC_ROOTS, seed_paths=PROOF_SEEDS
) -> list[tuple[str, str]]:
    vocabulary = derive_application_vocabulary(seed_paths)
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
                    try:
                        display = str(path.relative_to(ROOT))
                    except ValueError:
                        display = str(path)
                    hits.append((display, term))
    return sorted(set(hits))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("roots", nargs="*")
    parser.add_argument("--seed", action="append", dest="seeds")
    args = parser.parse_args()
    roots = tuple(Path(item) for item in args.roots) if args.roots else GENERIC_ROOTS
    seeds = tuple(Path(item) for item in args.seeds) if args.seeds else PROOF_SEEDS
    hits = vocabulary_hits(roots, seeds)
    for path, token in hits:
        print(f"{path}:{token}")
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
