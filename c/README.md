# UEM-16 C99 Interpreter (v0.1)

Dependency-free **C99** implementation of the Unified Event Machine.

## Independence rules

1. Semantics come from [`../UEM_SPEC.md`](../UEM_SPEC.md) and golden vectors only.
2. This is **not** a line-by-line translation of the Python host.
3. No Python runtime, no embedding, no calling generated domain packages.
4. No domain vocabulary (`invoice`, `text_stats`, …) in C sources.
5. `APPLY` only dispatches names listed in [`REGISTRY.md`](REGISTRY.md).
   Bytecode that references an unregistered primitive is rejected or fails as
   `unknown-primitive` (invalid, no ticket).

## What is proven

A target **passes** only when its **executable** runs the golden vectors and
matches the published expected traces (result JSON, state, evidence tail,
errors). Compilation alone is **not** chip support.

## Build (native)

```bash
cd c
make
./build/uem-c verify ../artifacts/uem/text_stats_v2/program.uem
./build/uem-c run ../artifacts/uem/text_stats_v2/program.uem --host '{"text":"Go go GO"}'
```

## Sanitizers

```bash
make asan
make ubsan
make test
```

## Cross builds (optional; pass only if binary runs vectors)

```bash
./scripts/build_cross.sh   # attempts arm64 / riscv64 / wasm32 when toolchains exist
```

## Differential proof

```bash
./scripts/gen_golden.sh    # Python reference → golden expected JSON
./scripts/diff_py_c.sh     # run C vs golden; exit nonzero on mismatch
```

## Layout

```text
include/uem.h       public API
src/                decode, machine, primitives, expr, ticket, host CLI
third_party/        cJSON (MIT), sha256 (public domain) — vendored, not packages
tests/vectors/      malformed bytecode + expected reject codes
tests/golden/       expected execution traces
REGISTRY.md         versioned generic primitive registry
```
