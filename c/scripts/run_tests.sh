#!/usr/bin/env bash
set -euo pipefail
CROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$CROOT"
make -s all
./scripts/gen_golden.sh
./scripts/diff_py_c.sh
echo "all C/UEM tests passed"
