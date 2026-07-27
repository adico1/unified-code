#!/usr/bin/env python3
"""Audit Thing v2's permanent בלי_מה surfaces against both proof seeds."""

from __future__ import annotations

import json
from pathlib import Path

from unified.generator.thing_v2 import (
    vocabulary_mutation_report,
    vocabulary_report,
)


ROOT = Path(__file__).resolve().parents[1]
SEEDS = (
    ROOT / "seed" / "thing_v2" / "trajectory_meter.json",
    ROOT / "seed" / "thing_v2" / "orchard_yield.json",
)


def main() -> int:
    seeds = tuple(json.loads(path.read_text(encoding="utf-8")) for path in SEEDS)
    absence = vocabulary_report(seeds)
    mutations = vocabulary_mutation_report(seeds)
    result = {
        "ok": absence["ok"] and mutations["ok"],
        "absence": absence,
        "mutations": mutations,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
