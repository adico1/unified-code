# Roadmap

## 0.1 — Kernel

- Canonical thing
- One-input/one-output parts
- Ten named depths
- 1D, 2D, and 3D spatial construction
- Evidence-bearing verification
- Conformance tests
- Explicit inward/outward boundaries (L7)
- Distinct unknown / absent / false / invalid states (L6)
- One-second construction law (L9) with `uc benchmark`

### Open (not decided in 0.1)

- Whether `world()` may append `world:composed` to an invalid thing, or
  must require `state == "valid"`. Recorded in SPEC.md; do not treat the
  current permissive behavior as law.

## 0.2 — Computation

- Choice as declarative event routes (L10)
- Repetition as audited `map_event` / `fold_event` / `until_quiet` (L10)
- Structured failure and `ticket.open` for unhandled exceptions (L10)
- Recursion forbidden as unaudited loop substitute
- Transformation examples (expression IR + event pipeline)

## 0.3 — Boundaries

- Files
- Standard input/output
- Time (clock_start / clock_end; L9 measurement)
- HTTP
- Persistence

## 0.4 — Construction

- Code that generates conforming parts
- Module assembly
- Project assembly
- Generated tests
- `uc new` / `uc add` generator (started in v0.1)
- Code-based `PROGRAM` / `FEATURE` declarations → runtime generation
  (not evidence-only stubs when `--declaration` is supplied)

## 0.5 — Translation

- Existing Python adapters
- JSON and HTTP adapters
- Comparison with functional composition, pipes, Unix filters, and
  dataflow systems

## 0.6 — Unified Event Machine (UEM-16)

- UEM-16 v0.1 spec + reference Python interpreter (`unified/machine/`)
- Canonical bytecode + SHA-256 program identity
- Declaration → symbolic → bytecode → execute (both proof domains)
- UEM gauntlet and measurements
- **Not yet:** replace generator; multi-ISA backends

### Next

- Minimal C interpreter of UEM-16
- Compile C core for x86-64, ARM64, RISC-V, selected MCUs
- Progressive reduction of residual Python control flow

## 1.0 candidate

- Formal grammar and semantics
- Reference evaluator
- Conformance suite
- Security and authority model
- Performance model
- Versioning and governance proposal
