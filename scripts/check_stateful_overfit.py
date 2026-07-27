#!/usr/bin/env python3
"""Prove proof-seed application vocabulary is absent from generic source."""

from __future__ import annotations

import argparse
from pathlib import Path

from unified.generator.overfit import vocabulary_hits


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("roots", nargs="*")
    parser.add_argument("--seed", action="append", dest="seeds")
    args = parser.parse_args()
    roots = tuple(Path(item) for item in args.roots) if args.roots else GENERIC_ROOTS
    seeds = tuple(Path(item) for item in args.seeds) if args.seeds else PROOF_SEEDS
    hits = vocabulary_hits(roots, seeds, display_root=ROOT)
    for path, token in hits:
        print(f"{path}:{token}")
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
