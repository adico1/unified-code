#!/usr/bin/env python3
"""Run Standard Ten provenance audit. Exit 1 if enforcement fails (expected until full seed expression)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from unified.standard_audit import enforce_ten, run_audit

    mode = (sys.argv[1] if len(sys.argv) > 1 else "audit").strip()
    if mode == "enforce":
        r = enforce_ten()
    else:
        r = run_audit()
    v = r.get("value") or {}
    print(json.dumps({
        "state": r.get("state"),
        "verdict": v.get("verdict") or (v.get("gap") or {}).get("kind"),
        "illegal_provenance_count": v.get("illegal_provenance_count"),
        "open_gap_count": v.get("open_gap_count"),
        "gap": v.get("gap"),
        "seed_sha256": v.get("seed_sha256"),
        "manifest_path": v.get("manifest_path"),
        "audit_path": v.get("audit_path"),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    # Audit mode always writes reports; exit 0 so humans can read gaps.
    # Enforce mode exits 1 on any standard.gap / fail verdict.
    if mode == "enforce":
        if r.get("state") == "invalid" or (v.get("verdict") not in {None, "pass"} and v.get("gap")):
            return 1
        if v.get("verdict") == "fail":
            return 1
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
