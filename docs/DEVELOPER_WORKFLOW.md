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

These are design targets, not measured claims:

```text
Generate project: seconds
Runnable small program: under 5 minutes
Generate ordinary feature: seconds
Complete familiar feature: 1–3 minutes
Unfamiliar domain logic: limited by domain understanding
```

The generator removes repeated structural decisions. It does not eliminate
domain reasoning. When the meaningful difference is hard, speed is limited
by understanding the domain—not by rewriting project scaffolding.

## Commands (v0.1)

```bash
uc new <project-name>
uc add <feature-name>
```

`uc new` creates a runnable UC-1 project. `uc add` inserts one new
one-input/one-output part into the existing nested composition and generates
its test.

## Relation to the laws

| Step | Law |
|---|---|
| One shape for every part | L1 |
| Nest operations in code | L2 |
| Opposed depths when axes appear | L3 |
| Complete dimensions | L4 |
| Evidence inside the thing | L5 |
| Distinct unknown / absent / false / invalid | L6 |
| Named inward / outward / write boundaries | L7 |
| Functions and plain data only | L8 |
