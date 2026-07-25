#!/usr/bin/env bash
# Clean-room partial regeneration under Standard Ten.
# Regenerates seed-locked UEM artifacts into a temp tree and compares
# byte-for-byte against committed artifacts.
#
# Does NOT claim full-repository regeneration (see gap.clean-room-full-tree).
# Exit 0 only when regenerable artifacts match. Open framework gaps do not
# pass this as full TEN completion — see AUDIT_STANDARD_TEN.md.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
[[ -x "$PY" ]] || PY=python3

WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

echo "=== Standard Ten clean-room (partial: UEM artifacts) ==="
echo "work: $WORKDIR"

# 1. Copy seed only (canonical input)
mkdir -p "$WORKDIR/seed"
cp -R "$ROOT/seed/." "$WORKDIR/seed/"

# 2. Need generator surface — until seed expresses framework, bootstrap from
#    current tree is a documented standard.gap dependency for regeneration.
#    Physical host + generator modules are temporary handwritten exception
#    until gap.seed-expresses-full-framework closes.
mkdir -p "$WORKDIR/bootstrap"
# Minimal PYTHONPATH: use live tree generator (gap) — recorded in report
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

ROOT="$ROOT" WORKDIR="$WORKDIR" "$PY" - <<'PY'
from pathlib import Path
import json, os, hashlib, sys

root = Path(os.environ["ROOT"])
work = Path(os.environ["WORKDIR"])
sys.path.insert(0, str(root))
from unified.standard_generate import generate_uem_from_seed_declaration
from unified.standard import load_seed

loaded = load_seed({"value": {"repo_root": str(root)}, "depths": (), "axes": (), "evidence": (), "state": "formed"})
if loaded.get("state") == "invalid":
    print(loaded)
    sys.exit(2)
seed = loaded["value"]["seed"]
results = []
for d in seed.get("declarations") or ():
    out_dir = work / "artifacts" / "uem" / d["id"]
    r = generate_uem_from_seed_declaration({
        **loaded,
        "value": {
            **loaded["value"],
            "declaration_path": str(root / d["path"]),
            "out_dir": str(out_dir),
        },
    })
    results.append({"id": d["id"], "state": r.get("state"), "out": str(out_dir)})
    if r.get("state") == "invalid":
        print(json.dumps(r.get("value"), indent=2, default=str))
        sys.exit(2)

mismatches = []
for d in seed.get("declarations") or ():
    for name in ("program.uem", "program.symbolic.json"):
        a = work / "artifacts" / "uem" / d["id"] / name
        b = root / "artifacts" / "uem" / d["id"] / name
        if not a.is_file():
            mismatches.append(f"missing-generated:{a}")
            continue
        if not b.is_file():
            mismatches.append(f"missing-committed:{b}")
            continue
        ha = hashlib.sha256(a.read_bytes()).hexdigest()
        hb = hashlib.sha256(b.read_bytes()).hexdigest()
        if ha != hb:
            mismatches.append(f"mismatch:{d['id']}/{name} gen={ha[:12]} committed={hb[:12]}")
        else:
            print(f"OK {d['id']}/{name} {ha[:16]}")

report = {
    "standard_version": "TEN-1",
    "scope": "partial-uem-artifacts",
    "full_tree_claimed": False,
    "gap": "gap.clean-room-full-tree",
    "results": results,
    "mismatches": mismatches,
    "verdict": "pass" if not mismatches else "fail",
}
(work / "clean_room_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
print(json.dumps(report, indent=2, sort_keys=True))
if mismatches:
    sys.exit(1)
print("clean-room partial PASS (UEM artifacts byte-identical)")
print("NOTE: full framework regeneration remains standard.gap — do not claim TEN complete")
PY

echo "=== done ==="
