#!/usr/bin/env bash
# Attempt cross builds. A target PASSES only if the binary runs golden vectors.
set -euo pipefail
CROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$CROOT"
mkdir -p build/cross
SRC="src/main.c src/decode.c src/machine.c src/primitives.c src/expr.c src/decimal.c third_party/cJSON.c third_party/sha256.c"
CFLAGS="-std=c99 -O2 -Iinclude -Ithird_party -Isrc -Wall"

try_build() {
  local name="$1"; shift
  echo "== build $name =="
  if "$@"; then
    echo "compiled $name"
    return 0
  else
    echo "skip $name (toolchain missing or failed)"
    return 1
  fi
}

# native already via make
make -s all
cp -f build/uem-c build/cross/uem-c-native || true

# arm64 (Apple silicon native or cross)
if command -v clang >/dev/null; then
  try_build arm64 clang $CFLAGS -target arm64-apple-macos -o build/cross/uem-c-arm64 $SRC || \
  try_build arm64-linux aarch64-linux-gnu-gcc $CFLAGS -o build/cross/uem-c-arm64 $SRC || true
fi

# riscv64
if command -v riscv64-linux-gnu-gcc >/dev/null; then
  try_build riscv64 riscv64-linux-gnu-gcc $CFLAGS -o build/cross/uem-c-riscv64 $SRC || true
fi

# wasm32
if command -v clang >/dev/null; then
  try_build wasm32 clang $CFLAGS -target wasm32-wasi --sysroot "${WASI_SYSROOT:-/}" \
    -o build/cross/uem-c.wasm $SRC 2>/dev/null || \
  try_build wasm32-emcc emcc $CFLAGS -o build/cross/uem-c.js $SRC 2>/dev/null || true
fi

echo "Cross artifacts in build/cross (run golden vectors on each before claiming support)."
