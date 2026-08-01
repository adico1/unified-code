# Unified Code

Unified Code is an experimental functional construction grammar for writing
software from one repeatedly practised form.

Start with [Vision](VISION.md), [Goals and boundaries](docs/GOALS_AND_BOUNDARIES.md),
[How to read the code](docs/HOW_TO_READ.md), and [Build output](docs/BUILD_OUTPUT.md).

[Read: The Age of AI Requires Standard Ten — One Unified Code for All Software](https://adico.tech/blog/2026/07/25/the-age-of-ai-requires-standard-ten-one-unified-code-for-all-software/)

```python
def part(thing):
    return thing
```

Parts are assembled directly inside other parts:

```python
result = outer(middle(inner(thing)))
```

> **Status: experimental research prototype**
>
> Unified Code currently demonstrates generated applications, event-driven
> domain composition, deterministic UEM-16 bytecode, and equivalent Python/C
> execution for published golden vectors.
>
> **Governing contract:** [STANDARD_TEN.md](STANDARD_TEN.md) (TEN-1) — one
> Thing, one seed, no handwritten application code, UEM-only execution.
> Conventional development is not an authorized fallback; unsupported work
> stops at `standard.gap`. Full-tree clean-room regeneration from seed alone
> is **not** claimed (open migration gaps in [AUDIT_STANDARD_TEN.md](AUDIT_STANDARD_TEN.md)).
>
> **Current verification:** functional suites and behavioral gauntlets
> **pass**, including full invoice Python/C differential (basic, empty,
> half-cent, reject paths). L13 multi-dimension coverage is **not closed**:
> **C lines 100% (1567/1567), C functions 100% (76/76), C branches incomplete
> ~78.19% (1115/1426).** Branch ledger: `c/tests/BRANCH_LEDGER.md`
> (`missing_arcs_measured` = `missing_arcs_in_ledger` + `unmapped_arcs`;
> currently 311 = 311 + 0; `unclassified_arcs` 0 — classified ≠ closed).
> Zero-total C coverage is failure, not 100%. See [GAUNTLET.md](GAUNTLET.md)
> and [coverage.json](coverage.json).
>
> **Hardware claim:** only targets with `native-pass` in
> `c/targets/manifests/` (today: host `x86_64`). ARM64 / RISC-V / MCU are
> not claimed without golden pass on real hardware.

The initial vocabulary is inspired by an engineering reading of *Sefer
Yetzirah*. This repository does not claim that the historical text is a
programming specification. It tests whether the following vocabulary can
become one:

```text
אות → עומק → ציר → מימד → דבר → עולם
letter → depth → axis → dimension → thing → world
```

## v0.1 claim

Hypotheses under test (not a finished product standard). The machine and
gauntlets below are real implementation layers of the same prototype.

1. Every public operation has one input and one output.
2. A depth is an oriented interface.
3. An axis is a pair of opposing depths.
4. An `n`-dimensional interface contains `2n` oriented depths.
5. Larger programs are code-based recursive compositions of smaller parts.

## Run in 60 seconds

Requires Python 3.11 or newer.

```bash
git clone https://github.com/adico1/unified-code.git
cd unified-code
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test]"
pytest
uc new generated-demo
cd generated-demo
pytest
python -m generated_demo
```

## Small example

```python
from unified import inward, letter, outward, space, verify, world

result = outward(world(verify(space(letter(inward("seed"))))))
```

`inward` / `outward` are visible boundaries (L7). `letter` accepts a
canonical thing, not a bare host value (L1). States `unknown`, `absent`,
`false`, and `invalid` are distinct (L6).

## Complete-contract tool

The full acceptance plan (branch baseline, L13 closure, `uc unfold`,
task-ledger seed proof, Standard Ten, publish) is machine-checked by one
script:

```bash
./scripts/uc_contract plan          # ordered phases P0–P6
./scripts/uc_contract status        # live pass/fail criteria
./scripts/uc_contract conservation  # baseline equation only
./scripts/uc_contract ledger        # regenerate branch ledger
./scripts/uc_contract verify        # full gates (pytest/C/L13/audit)
./scripts/uc_contract report        # honest 14-point final report
```

Stateful seed-to-application product:

```bash
uc unfold seed/declarations/task_ledger.json \
  --output /tmp/uc-task-ledger \
  --verify \
  --run
```

Universal calculator generation is documented in
[CALCULATOR_GENERATOR.md](CALCULATOR_GENERATOR.md). Seven reference
calculators and an unseen eighth composition are derived from atomic,
versioned seeds with:

```bash
uc calculator generate-suite seed/calculator_suite.json \
  --output /tmp/unified-calculator-suite \
  --build --install --verify --gauntlet-depths 10
```

Milestone 1.1 removes the original task-ledger profile behavior from the generic
generator. Its independent numeric-transition proof is:

```bash
uc unfold seed/declarations/score_board.json \
  --output /tmp/uc-score-board \
  --verify \
  --run
```

Both applications declare their schema, commands, arguments, validation,
transitions, results, errors, persistence identity, composition, and acceptance
scenarios in JSON. Python and C independently execute the same seed-defined
transition program for every sequential acceptance and rejection step, including
post-state, result, error, ticket, and evidence equality.
`scripts/check_stateful_overfit.py` derives application vocabulary from every
proof seed and rejects it in generic generator and UEM runtime source. Its
contextual command check rejects task-ledger `add` comparisons in the stateful
runtime without confusing them with the registered generic expression operator.
The frozen stateful scalar profile is specified in `UEM_SPEC.md`; generated
Python, Python UEM, and C UEM share its ASCII integer grammar, exact JSON range,
and explicit ASCII-only `non_empty` whitespace rule.

Full repository self-hosting is tracked separately as “Milestone 2 — Root-seed
fixed-point bootstrap” in `ROADMAP.md`; it does not block this application
contract.

The bounded pre-bootstrap trust boundary and deterministic Stage-1 handoff are
specified in [STAGE0.md](STAGE0.md). The structured root-seed declaration now
generates the first isolated runnable framework/generator surface described in
[STAGE1.md](STAGE1.md), without widening the application-language surface. Its
isolated byte-identical two-stage proof is documented in
[STAGE1_FIXED_POINT.md](STAGE1_FIXED_POINT.md).

The complete dependency-aware verification graph is executed once with
[`uc verify-all`](VERIFY_FLOW.md), with tool bootstrap measured separately from
the enforced five-second evidence-verification budget.

### Thing v2 — compile-time specialization

Thing v2 specializes seven seedless (`בלי_מה`) boilerplate responsibilities at
compile time. The generated application runs without loading the seed or
requiring the source repository:

```bash
uc compile seed/thing_v2/trajectory_meter.json \
  --output /tmp/uc-trajectory-meter \
  --verify
```

The native and foreign-fixture proofs, seed schema, exact stage map,
deterministic manifest, affected-file churn contract, anti-overfitting
mutations, and honest limitations are specified in
[THING_V2.md](THING_V2.md).

### Generated applications, one assembly

The application-generation milestone combines the original Thing v2 proof
products with the seed-defined application-language catalog. One public command
builds and verifies every currently proven profile without handwritten
application code or tests. The original proofs retain responsive browser
interfaces and real-browser CLI/GUI differential evidence; the catalog retains
its generated GUI self-verification. The generated `build/` entrance exposes
six product families directly; compiler-private trees and evidence live under
`build/.unified/`. [Browse all generated product sources](build/README.md),
follow the [reading guide](docs/HOW_TO_READ.md), or inspect the assembly contract
in [APPLICATION_ASSEMBLY.md](APPLICATION_ASSEMBLY.md).

```bash
uc assemble seed/application_suite.json \
  --output build \
  --build --install --verify --gauntlet-depths 10
```

Qualified names can resolve through a pinned, content-addressed registry to
one verified artifact through the current Application v3, application-language,
Thing v2, stateful, or expression/UEM compiler route without implicit version
selection. The
bounded resolution and artifact lifecycle are specified in
[MANIFESTATION.md](MANIFESTATION.md).

Exit code is nonzero until every criterion is green. Do not claim
completeness while `contract_pass` is false. Writes `contract_status.json`
/ `contract_report.json` under the repo root when verify/report run.

## Developer workflow

Learn one construction process once and use it everywhere. The developer
supplies only the meaningful difference; the generator supplies the
repeated structure.

```bash
uc new my-project
cd my-project
pytest
python -m my_project
uc add double
```

### L9 — One-second construction

After a complete declaration, `uc new` and `uc add` (validation through
filesystem publication and evidence) must each complete in **≤ 1 second**
on ordinary local hardware. Measure with:

```bash
uc benchmark --iterations 20
```

### L10 — Event-Driven Flow

**Precise achievement:** generated domain logic and composition are
event-driven; imperative control flow is confined to named runtime
primitives and boundaries. The full runtime and generator are **not**
yet fully event-driven.

```python
ROUTES = {
    "program.start": on_program_start,
    "exception.unhandled": construct_ticket,
    "ticket.persist.requested": outward_ticket_store,
    "ticket.persisted": fail_with_ticket,
}

def program(thing):
    return until_quiet(enqueue(emit(thing, "program.start"), "program.start"), ROUTES)
```

Audited primitives carry formal contracts and direct tests. Ticket
construction is pure; persistence is a separate outward boundary
(`outward_ticket_store`) with atomic write and emergency-on-failure
(no recursive ticket).

See [docs/DEVELOPER_WORKFLOW.md](docs/DEVELOPER_WORKFLOW.md) for the full
sequence, scales (UC-0 through UC-4), and L9 measurement scope.

### UEM-16 v0.1 — Unified Event Machine (foundation)

Chip-neutral 16-opcode machine beneath Unified Code. The existing generator
is **not** replaced; both domains compile and execute through UEM with
identical external JSON. Spec: [UEM_SPEC.md](UEM_SPEC.md).

```bash
python -c "from unified.machine.compile_decl import compile_declaration_path; from unified.machine.thing import value_of; t=compile_declaration_path('examples/declarations/text_stats_v2.py'); print(value_of(t).get('program_sha256','')[:16], t.get('state'))"
```

### L12 — Physical-Target Conformance

A target is **supported** only when its native executable runs the unchanged
golden suite with byte-identical canonical results. See `c/targets/manifests/`.

```bash
cd c && make l12
```

Status vocabulary: `native-pass` | `emulated-pass` | `compile-only` | `unavailable`.

Not claimed without hardware golden pass: ARM64, RISC-V, MCU families.
Wasm goldens in ≥2 runtimes = Wasm-host support (not chip support).

See [SPEC.md](SPEC.md), [LAW.md](LAW.md), and [ROADMAP.md](ROADMAP.md).


### L13 — Complete Testing Gauntlet

Multi-dimensional 100% coverage (statements, branches, opcodes, primitives,
spec traceability, mutations, differential, physical goldens, fuzz 100k).
Never one averaged score. The build **must** fail if any dimension is below 100%.

```bash
./scripts/run_l13.sh
```

Emits `coverage.json` and `GAUNTLET.md`.

**Current result: FAIL.** Behavioral dimensions and Python code coverage
pass (invoice Py/C differential restored). **C lines and functions pass**;
**C branches do not** (1115/1426 under arc enumeration). Allocator fault
injection is in place (`uem_allocator` / `fail_after`); branch work is
tracked in `c/tests/BRANCH_LEDGER.md` with reconciliation fields
(`missing_arcs_measured`, `unmapped_arcs`, `unclassified_arcs`,
`resolved_arcs` on stable `arc_id`). L13 branch eligibility requires all
three missing/unmapped/unclassified counters at zero. Zero denominators
fail the gate—they never count as 100%. See [GAUNTLET.md](GAUNTLET.md)
and [coverage.json](coverage.json). If a local run differs, trust the
files that `run_l13.sh` just wrote.

### Standard Ten (governing contract)

Compact rules live in [STANDARD_TEN.md](STANDARD_TEN.md). Run:

```bash
./scripts/run_standard_ten.sh
```

| Artifact | Role |
| --- | --- |
| `STANDARD_TEN.md` | Ten rules + non-fallback law |
| `seed/ROOT.seed.json` | Canonical seed |
| [`ROOT_CONVERGENCE.md`](ROOT_CONVERGENCE.md) | Projection/root fixed-point, watcher, authority and בלימה law |
| `seed/ROOT_CONVERGENCE_SCHEMA.json` | Executable convergence-trace contract |
| `seed/declarations/*.json` | Pure-data app declarations |
| `PROVENANCE_MANIFEST.json` | Every file classified |
| `AUDIT_STANDARD_TEN.md` | Human audit + open `standard.gap` |

Partial clean-room: UEM artifacts regenerate byte-identical from seed declarations.  
**Full-tree clean-room is not claimed** while open gaps remain. Enforcement fails until every file is one of: `seed` | `generated` | `external-vendored` | `physical-host-boundary` | `evidence`.

<!-- BEGIN UC GENERATED ISSUE7:status:a7bfb9771dc823536d7d4fc4af46432579faddd4f5e430d2d449c2153343f827 -->
## Generated verification status

Authority: `90074d90922f343b1f807dd2756f3370d52776a1d2c536fc85b8b7f9c9e1d06a`
Semantic structure: `d1fcd43879f432e7abd07d52170c0fab09cbc26d6fa68e699c641fa4e5ab95e3`
Canonical facts: `75`
Generated test partitions: `80`
Generated behavioral mutations: `20`
Generated canonical goldens: `74`
Verification proof nodes: `24`

Target status:

- `posix`: `declared-unverified`; support claim `false`
- `wasm`: `declared-unverified`; support claim `false`
- `mcu`: `declared-unverified`; support claim `false`
- `python-host`: `declared-unverified`; support claim `false`

Open Milestone 2 gaps remain visible:

- `gap.seed-expresses-full-framework`: `open`
- `gap.no-app-control-flow-in-host`: `open`
- `gap.oop-exprfail`: `closed`
- `gap.declarations-as-python`: `open`
- `gap.dual-host-not-single-machine-surface`: `design-ticket`
- `gap.generated-tests-and-docs`: `open`
- `gap.clean-room-full-tree`: `open`

Issue #7 does not claim new hardware support, external dependency provenance, or whole-repository clean-room regeneration.
<!-- END UC GENERATED ISSUE7:status -->
