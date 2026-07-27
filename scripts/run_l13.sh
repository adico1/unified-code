#!/usr/bin/env bash
# L13 Complete Testing Gauntlet — fails unless every dimension is 100%.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PYTHON_BIN="${PYTHON:-python3}"
if [[ -x .venv/bin/python ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

echo "=== ensure C posix binary ==="
make -C c posix CFLAGS="-std=c99 -Wall -O2 -Iinclude -Ithird_party -Icore -Ihost/mcu"

echo "=== L12 native report (physical target) ==="
"$PYTHON_BIN" c/scripts/run_l12_report.py >/tmp/l12.json || true

echo "=== pytest production tests ==="
UEM_C="$ROOT/c/build/uem-c" "$PYTHON_BIN" -m pytest \
  tests/test_l13.py tests/test_l13_deep.py tests/test_l13_coverage.py \
  tests/test_l11.py tests/test_uem.py -q --tb=line

echo "=== L13 gauntlet (all dimensions) ==="
UEM_C="$ROOT/c/build/uem-c" "$PYTHON_BIN" - <<'PY'
from unified.machine.l13 import run_l13_gauntlet
from unified.machine.thing import value_of
r = run_l13_gauntlet()
rep = value_of(r)
print("L13 verdict:", rep.get("verdict"))
dims = rep.get("dimensions") or {}
for k, d in sorted(dims.items()):
    ok = "OK" if d.get("ok") else "FAIL"
    act = d.get("actual", d.get("score"))
    print(f"  [{ok}] {k}: {act}")
if rep.get("verdict") != "pass":
    raise SystemExit(1)
print("coverage.json and GAUNTLET.md written")
PY

echo "L13 PASS"
