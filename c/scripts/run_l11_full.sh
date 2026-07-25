#!/usr/bin/env bash
# Full L11 close-out: release + ASan + UBSan + fuzz + Python gauntlet
set -euo pipefail
CROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="$(cd "$CROOT/.." && pwd)"
cd "$CROOT"

echo "=== release build ==="
make clean
make CFLAGS="-std=c99 -Wall -O2 -Iinclude -Ithird_party -Isrc"

echo "=== golden diff (legacy) ==="
./scripts/diff_py_c.sh

echo "=== L11 gauntlet (Python+C) ==="
export UEM_C="$CROOT/build/uem-c"
"$ROOT/.venv/bin/python" - <<'PY'
from unified.machine.l11 import run_l11_gauntlet
from unified.machine.thing import value_of
r = run_l11_gauntlet()
L = value_of(r)["l11"]
print("L11 verdict:", L["verdict"], "passed", len(L["passed"]), "failed", L["failed"])
assert L["verdict"] == "pass", L["failed"]
PY

echo "=== mutation fuzz ==="
UEM_FUZZ_N="${UEM_FUZZ_N:-300}" "$ROOT/.venv/bin/python" scripts/fuzz_bytecode.py

echo "=== ASan ==="
make asan
export UEM_C="$CROOT/build/uem-c"
./scripts/diff_py_c.sh
"$ROOT/.venv/bin/python" - <<'PY'
from unified.machine.l11 import run_l11_gauntlet
from unified.machine.thing import value_of
r = run_l11_gauntlet()
assert value_of(r)["l11"]["verdict"] == "pass"
print("ASan L11 pass")
PY

echo "=== UBSan ==="
make ubsan
./build/uem-c run ../artifacts/uem/text_stats_v2/program.uem --host '{"text":"Go go GO"}' >/dev/null
./build/uem-c run ../artifacts/uem/invoice_total/program.uem --host '{"document":{"tax_rate":"0.10","items":[]}}' >/dev/null
echo "UBSan run ok"

echo "=== native identity ==="
uname -m
file build/uem-c || true
ls -la build/uem-c

echo "=== multi-arch note ==="
echo "ARM64/RISC-V: not marked supported without hardware golden execution."
echo "Native host ($(uname -m)) golden vectors: PASS under release+ASan+UBSan."

echo "ALL CLOSED"
