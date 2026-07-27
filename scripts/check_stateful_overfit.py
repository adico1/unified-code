#!/usr/bin/env python3
"""Fail when persistent-application vocabulary leaks into generic generation."""

from __future__ import annotations

import argparse
from pathlib import Path


DOMAIN_TERMS = (
    "task",
    "tasks",
    "title",
    "completed",
    "invalid-title",
    "duplicate-title",
    "task-not-open",
    "uc_task_ledger_state",
)
PROFILE_COMMANDS = ("add", "complete", "list")


def vocabulary_hits(root: Path) -> list[tuple[str, str]]:
    hits = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for token in DOMAIN_TERMS:
            if token in text:
                hits.append((str(path.relative_to(root)), token))
    emitter = root / "stateful_emit.py"
    if emitter.is_file():
        text = emitter.read_text(encoding="utf-8")
        for command in PROFILE_COMMANDS:
            for quote in ('"', "'"):
                pattern = f"command == {quote}{command}{quote}"
                if pattern in text:
                    hits.append(("stateful_emit.py", pattern))
    return hits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "root",
        nargs="?",
        default=str(Path(__file__).resolve().parents[1] / "unified" / "generator"),
    )
    args = parser.parse_args()
    hits = vocabulary_hits(Path(args.root))
    for path, token in hits:
        print(f"{path}:{token}")
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
