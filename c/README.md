# UEM-16 C implementation

## Layout (L12)

```text
core/           portable machine (decode, execute, primitives)
host/posix/     files, stdout, CLI
host/wasm/      Wasm entry (Wasm-host ≠ chip support)
host/mcu/       UEM-MCU-1 bounded profile surface
include/uem.h   public API
targets/manifests/  L12 result reports
tests/golden/   expected traces
tests/fuzz_corpus/  saved fuzz seeds
tests/regressions/  permanent failures from fuzz
```

## Build

```bash
make posix          # native host binary: build/uem-c
make mcu            # MCU profile demo: build/uem-mcu-demo
make wasm-compile   # optional wasm32-wasi artifact
make l12            # native golden report → targets/manifests/
```

## L12 support rule

A processor target is **supported** only when its **native** executable runs
the unchanged golden suite with **byte-identical** canonical results.

| Status | Meaning |
| --- | --- |
| native-pass | Goldens on real hardware, results match |
| emulated-pass | Emulator evidence only (not chip support) |
| compile-only | Built, not executed on target |
| unavailable | No toolchain/hardware here |

## Independence

Semantics from `../UEM_SPEC.md` and goldens. No Python runtime in C.
`APPLY` only dispatches `REGISTRY.md` names.
