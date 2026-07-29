# Developer workflow

## Objective

Learn one construction process once and use it everywhere. The developer
supplies only the meaningful difference; the generator supplies the
repeated structure.

## Standard developer sequence

```text
describe difference
generate parts
assemble parts
verify construction
run program
```

## Developer supplies

```text
intent
input meaning
transformation rule
invariant
required external authority
```

## Generator supplies

```text
project structure
files
imports
canonical thing
inward/outward boundaries
nested composition
validation
error/state representation
tests
documentation
entry point
```

## Recursive construction

```text
Law
└── generates generator
    └── generates project
        └── generates feature
            └── generates tests and evidence
```

The same laws apply at every layer. Each layer returns a canonical thing
with evidence. Effects cross named boundaries only.

## Project scales

```text
UC-0: expression
UC-1: script
UC-2: application
UC-3: service
UC-4: system
```

All scales use the same laws. Smaller scales must not be forced to generate
unnecessary layers. A UC-1 script has boundaries, composition, and tests; it
does not need service deployment scaffolding.

## Target developer speed

**L9 — One-second construction** (user-originated core rule):

```text
Generate project (uc new):   ≤ 1 second   (measured: validation → write → evidence)
Generate feature (uc add):   ≤ 1 second   (same measured interval)
```

The measured interval includes validation, source generation, composition,
structural verification, filesystem writes, and result/evidence
construction. It excludes human reasoning, human input time, dependency
installation, network operations, and running the generated program’s
complete test suite.

Additional design targets (not L9):

```text
Runnable small program after generation: under 5 minutes
Complete familiar feature (including domain edits): 1–3 minutes
Unfamiliar domain logic: limited by domain understanding
```

The generator removes repeated structural decisions. It does not eliminate
domain reasoning. When the meaningful difference is hard, speed is limited
by understanding the domain—not by rewriting project scaffolding.

## Commands (v0.1)

```bash
uc new <project-name>
uc new <project-name> --declaration path/to/program.py
uc add <feature-name>
uc add <feature-name> --declaration path/to/feature.py
uc build path/to/declaration.py
uc gauntlet
uc gauntlet path/to/declaration.py
uc gauntlet path/to/generated/project
uc benchmark
uc benchmark --iterations 20
```

`uc new` without a declaration creates a scaffold (architectural shape).
`uc new --declaration` loads a code-based `PROGRAM` dict and generates
runtime parts, boundaries, CLI, presentation, verify rules, and tests from
that plain-data declaration.

`uc add` without a declaration inserts an evidence-only stub (historical
behavior). `uc add --declaration` loads a `FEATURE` dict with:

```text
input shape
transformation
invariants
boundaries
errors
presentation (via program)
tests
```

Declarations are Python modules defining `PROGRAM` or `FEATURE` as dicts.
No YAML. No classes.

See `examples/declarations/text_stats_program.py` for a full program that
regenerates the text-statistics application with near-zero manual runtime
code.

`uc benchmark` measures real `new` and `add` against L9 on the
local machine (authoritative for the one-second rule).

Local wall-clock integration command:

```bash
uc benchmark --iterations 20
# equivalent:
python -m unified.generator.benchmark
```

## Relation to the laws

| Step | Law |
|---|---|
| One shape for every part | L1 |
| Nest operations in code | L2 |
| Opposed depths when axes appear | L3 |
| Complete dimensions | L4 |
| Evidence inside the thing | L5 |
| Distinct unknown / absent / false / invalid | L6 |
| Named inward / outward / write / clock boundaries | L7 |
| Functions and plain data only | L8 |
| Construction ≤ 1 second after declaration | L9 |

<!-- BEGIN UC GENERATED ISSUE7:workflow:94f7f963f948126345e372dc73aac203608b6731b7b8af4cfb9fa2cd70ec32b3 -->
# Generated verification workflow

Authority: `c064b67c6b0074835ea215e2a89fd9b014ab31d615ef8a7e3e3a6f9176a31032`
Semantic structure: `c21b3e04a89002ecf7bcfd935981e7886d376374ec529a65562a9e2eb627b0a6`
Canonical facts: `59`
Generated test partitions: `80`
Generated behavioral mutations: `20`
Generated canonical goldens: `74`
Verification proof nodes: `24`

Run `uc verify-all`. Modify canonical seed declarations, regenerate the projection tree, and never edit generated regions or generated files directly.

Generation flow:

```text
verification-generation.requested
authorities.resolved
contracts.projected
tests.generated
mutations.generated
goldens.generated
documentation.generated
audits.generated
projections.cross-checked
fixed-point.requested
fixed-point.completed
verification.requested
verification.completed
```
<!-- END UC GENERATED ISSUE7:workflow -->
