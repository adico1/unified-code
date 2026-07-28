"""Content-addressed admission boundary for the physical L13 CI proof."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATHS = (
    "GAUNTLET.md",
    "c/targets/manifests/l12_report_x86_64.json",
    "coverage.json",
    "coverage_py.json",
)


def audited_l13_evidence_boundary():
    provenance = json.loads(
        (ROOT / "PROVENANCE_MANIFEST.json").read_text(encoding="utf-8")
    )
    entries = {item["path"]: item for item in provenance["files"]}
    identities = {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        for path in EVIDENCE_PATHS
    }
    assert all(entries[path]["sha256"] == digest for path, digest in identities.items())
    coverage = json.loads((ROOT / "coverage.json").read_text(encoding="utf-8"))
    assert coverage["verdict"] == "pass"
    assert all(item["ok"] for item in coverage["dimensions"].values())
    native = json.loads(
        (ROOT / "c/targets/manifests/l12_report_x86_64.json").read_text(
            encoding="utf-8"
        )
    )
    assert native["l12"] is True
    assert native["native_evaluation"]["mismatches"] == 0
    assert native["targets"][0]["status"] == "native-pass"
    return {
        "verdict": "pass",
        "identities": identities,
        "dimensions": len(coverage["dimensions"]),
    }


print(json.dumps(audited_l13_evidence_boundary(), sort_keys=True))
