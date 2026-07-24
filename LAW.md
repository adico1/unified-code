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

## L7 — No hidden effects

Input/output, time, randomness, persistence, and network access must be
visible boundary parts.

## L8 — No object hierarchy

The core uses functions and plain data. It requires no classes or
inheritance.
