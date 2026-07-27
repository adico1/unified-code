# Roadmap

## Milestone 1 — Seed-to-application product

Public contract:

```bash
uc unfold seed/declarations/task_ledger.json \
  --output /tmp/uc-task-ledger \
  --verify \
  --run
```

This checkpoint proved the complete task-ledger product pipeline: one JSON seed
configured a prebuilt persistent-resource profile, generated its runnable
application and tests, verified deterministic rebuild hashes, and installed
only after every requested gate passed.

The later Milestone 1.1 audit found that this checkpoint's Python/C result check
transported Python's completed payload through a literal UEM program. It did not
prove independent cross-host application behavior. The generation and product
proof remained valid; the equality claim was superseded by Milestone 1.1.

## Milestone 1.1 — Generic seed-defined stateful behavior

Issue [#11](https://github.com/adico1/unified-code/issues/11) corrects an
overfitting defect found after the Milestone 1 checkpoint. Application-domain
commands, fields, validation, transitions, results, errors, persistence
identity, composition, and acceptance scenarios must originate in the seed,
not in the generic generator.

The acceptance proof uses two independent applications:

```bash
uc unfold seed/declarations/task_ledger.json \
  --output /tmp/uc-task-ledger \
  --verify \
  --run

uc unfold seed/declarations/score_board.json \
  --output /tmp/uc-score-board \
  --verify \
  --run
```

Milestone 1.1 does not depend on or widen Milestone 2.

Both hosts now execute one generic UEM transition program derived from each
seed. Every step compares resulting state, result, evidence, errors, and ticket
status. Declared duplicate/missing-resource errors are exercised inside the
persisted sequence, followed by successful recovery commands and restart.
Generated Python, Python UEM, and C UEM also share the frozen scalar input
profile in `UEM_SPEC.md`, with differential minimum, maximum, overflow, syntax,
Unicode-digit, and whitespace vectors.

## Milestone 2 — Root-seed fixed-point bootstrap

This milestone is deliberately non-blocking for Milestone 1. Open items:

- Generate the generator and complete framework from `seed/ROOT.seed.json`.
- Generate Python/C hosts, physical target adapters, and build definitions.
- Generate repository tests, mutations, goldens, documentation, and audit tools.
- Account for vendored dependencies without claiming they were generated.
- Rebuild the complete repository in a clean room from Stage 0 plus the root
  seed.
- Reach a whole-tree fixed point with byte-identical hashes.
- Unify the UEM surface while preserving independent Python and C hosts for
  L11 equivalence.

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

### 0.7 — L12 Physical targets

- Portable core vs host split (`c/core`, `c/host/*`)
- Target manifests and golden-on-hardware rule
- UEM-MCU-1 profile (no family claim without board)
- Strengthened fuzz corpus (≥100k)

### 0.8 — L13 Complete Testing Gauntlet (done)

- Multi-dimension coverage gate — every dimension exactly 100%
- coverage.json + GAUNTLET.md emitters; CI job fails on any miss
- Catalogs: opcodes, primitives, tickets, mutations, differential, states, events
- Python statement/branch 100%; C line/function/branch 100% (vendored separate)
- No pragma/no-cover; production paths only in primary score

### 0.9 — Standard Ten (governing contract — in force, migration open)

- `STANDARD_TEN.md` TEN-1 + non-fallback law
- Canonical seed `seed/ROOT.seed.json` + pure JSON declarations
- `standard.gap` only response to unsupported expression
- Provenance audit + clean-room partial (UEM artifacts)
- **Not complete:** full clean-room regeneration of framework/hosts/tests/docs from seed alone (open gaps in seed)

### Next / in progress (Milestone 2)

- Close `standard.gap` tickets by seed-expressing packages (no conventional fill)
- Eliminate OOP (`_ExprFail`) via plain-data faults
- Unify the UEM surface while preserving independent Python and C hosts for
  L11 equivalence
- Optional: ARM64 / RISC-V / wasm executables after vector pass on-device
- Formal grammar and semantics toward 1.0

## 1.0 candidate

- Formal grammar and semantics
- Reference evaluator
- Conformance suite
- Security and authority model
- Performance model
- Versioning and governance proposal
