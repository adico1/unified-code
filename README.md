# Unified Code

**Governing contract: [STANDARD_TEN.md](STANDARD_TEN.md) (TEN-1).**  
Conventional development is not an authorized fallback. Unsupported work stops at `standard.gap`.

Unified Code is an experimental functional construction grammar for writing
software from one repeatedly practised form.

[Read: The Age of AI Requires Standard Ten — One Unified Code for All Software](https://adico.tech/blog/2026/07/25/the-age-of-ai-requires-standard-ten-one-unified-code-for-all-software/)

```python
def part(thing):
    return thing
```

Parts are assembled directly inside other parts:

```python
result = outer(middle(inner(thing)))
```

The initial vocabulary is inspired by an engineering reading of *Sefer
Yetzirah*. This repository does not claim that the historical text is a
programming specification. It tests whether the following vocabulary can
become one:

```text
אות → עומק → ציר → מימד → דבר → עולם
letter → depth → axis → dimension → thing → world
```

## v0.1 claim

1. Every public operation has one input and one output.
2. A depth is an oriented interface.
3. An axis is a pair of opposing depths.
4. An `n`-dimensional interface contains `2n` oriented depths.
5. Larger programs are code-based recursive compositions of smaller parts.

These are hypotheses under test, not yet a software standard.

## Run

```bash
python -m unified
python -m pytest
uc benchmark --iterations 20
```

## Small example

```python
from unified import inward, letter, outward, space, verify, world

result = outward(world(verify(space(letter(inward("seed"))))))
```

`inward` / `outward` are visible boundaries (L7). `letter` accepts a
canonical thing, not a bare host value (L1). States `unknown`, `absent`,
`false`, and `invalid` are distinct (L6).

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
python -c "from unified.machine import compile_declaration_path; ..."
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
spec traceability, mutations, differential, physical goldens). Never one averaged score.

```bash
./scripts/run_l13.sh
```

Emits `coverage.json` and `GAUNTLET.md`. Build fails if any dimension is below 100%.

### Standard Ten (governing contract)

```bash
./scripts/run_standard_ten.sh
```

| Artifact | Role |
| --- | --- |
| `STANDARD_TEN.md` | Ten rules + non-fallback law |
| `seed/ROOT.seed.json` | Canonical seed |
| `seed/declarations/*.json` | Pure-data app declarations |
| `PROVENANCE_MANIFEST.json` | Every file classified |
| `AUDIT_STANDARD_TEN.md` | Human audit + open `standard.gap` |

Partial clean-room: UEM artifacts regenerate byte-identical from seed declarations.  
**Full-tree clean-room is not claimed** while open gaps remain. Enforcement fails until every file is one of: `seed` | `generated` | `external-vendored` | `physical-host-boundary` | `evidence`.
