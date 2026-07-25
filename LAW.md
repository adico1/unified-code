# Laws

## L1 — One shape

Every public operation accepts one thing and returns one thing.

```python
def part(thing):
    return thing
```

## L2 — Code constructs code

Composition is expressed by nesting operations, not by a separate
configuration language.

```python
outer(middle(inner(thing)))
```

## L3 — Opposed depths

One complete axis contains two named, opposing interfaces.

## L4 — Dimensional completeness

An interface with `n` axes contains exactly `2n` depths.

## L5 — Explicit evidence

Verification returns its verdict and evidence as part of the thing.

## L6 — Unknown is not false

Unknown, absent, invalid, and false are distinct states.

```text
unknown  — admitted, not yet classified
absent   — value is None
false    — value is False
invalid  — failed verification or rejected shape
```

## L7 — No hidden effects

Input/output, time, randomness, persistence, and network access must be
visible boundary parts.

```python
outward(world(verify(space(letter(inward(host_value))))))
```

`inward` admits host values; `outward` records emission. Kernel parts do
not print, write, or call the network.

## L8 — No object hierarchy

The core uses functions and plain data. It requires no classes or
inheritance.

## L9 — One-second construction

After a complete declaration is supplied, project or feature generation,
assembly, structural verification, and filesystem publication must complete
in at most one second on ordinary local hardware.

```text
limit = 1_000_000_000 nanoseconds
```

### Measured interval includes

```text
validation
source generation
composition
structural verification
filesystem writes
result/evidence construction
```

### Measured interval excludes

```text
human reasoning
human input time
dependency installation
network operations
running the generated program’s complete test suite
```

This is a user-originated core rule. Time is read only through a named
clock boundary (L7). L9 PASS requires both `uc new` and `uc add` p95
durations ≤ 1 second and every measured generation result `valid`.
