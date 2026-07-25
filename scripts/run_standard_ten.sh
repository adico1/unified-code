#!/usr/bin/env bash
# Standard Ten gate suite.
# 1) Load seed  2) Generate UEM from seed declarations  3) Audit  4) Clean-room partial
# Full-tree TEN pass is NOT claimed while open gaps remain.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
[[ -x "$PY" ]] || PY=python3
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
export ROOT WORKDIR=""

echo "=== 1. STANDARD_TEN.md present ==="
test -f STANDARD_TEN.md

echo "=== 2. Load seed ==="
"$PY" - <<'PY'
from unified.standard import load_seed
r = load_seed({"value": {}, "depths": (), "axes": (), "evidence": (), "state": "formed"})
assert r["state"] == "formed", r
print("seed_sha256", r["value"]["seed_sha256"])
print("open_gaps", len(r["value"]["seed"].get("gaps") or []))
PY

echo "=== 3. Generate UEM from seed declarations ==="
"$PY" - <<'PY'
from unified.standard_generate import generate_all_seed_declarations
r = generate_all_seed_declarations()
assert r.get("state") != "invalid" or (r.get("value") or {}).get("gap"), r
print("generated", (r.get("value") or {}).get("generated"))
print("generator_sha256", (r.get("value") or {}).get("generator_sha256", "")[:16])
PY

echo "=== 4. Provenance audit (writes PROVENANCE_MANIFEST.json) ==="
"$PY" scripts/audit_standard_ten.py audit

echo "=== 5. standard.gap smoke ==="
"$PY" - <<'PY'
from unified.standard import standard_gap, refuse_conventional
g = standard_gap({"value": {"gap_id": "gap.test", "rule": "3", "summary": "smoke"}, "depths": (), "axes": (), "evidence": (), "state": "formed"})
assert g["state"] == "invalid"
assert "standard.gap" in g["evidence"]
assert g["value"]["ticket"]["kind"] == "standard.gap"
r = refuse_conventional({"value": {"summary": "would use OOP"}, "depths": (), "axes": (), "evidence": (), "state": "formed"})
assert r["state"] == "invalid"
print("standard.gap OK")
PY

echo "=== 6. Clean-room partial ==="
export WORKDIR
ROOT="$ROOT" bash scripts/clean_room_ten.sh

echo "=== 7. Enforcement (expected fail while gaps open) ==="
set +e
"$PY" scripts/audit_standard_ten.py enforce
ENF=$?
set -e
echo "enforce_exit=$ENF"
if [[ "$ENF" -eq 0 ]]; then
  echo "UNEXPECTED: enforcement passed — only valid when all gaps closed and full clean-room works"
else
  echo "enforcement correctly reports standard.gap (open migration)"
fi

echo "=== Standard Ten suite complete ==="
echo "Completion claim: FORBIDDEN until clean empty directory regenerates full tree."
echo "See AUDIT_STANDARD_TEN.md and seed/ROOT.seed.json gaps."
