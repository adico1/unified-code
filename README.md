# Unified Code

Unified Code is an experimental functional construction grammar for writing
software from one repeatedly practised form.

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
```

## Small example

```python
from unified import letter, space, verify, world

result = world(verify(space(letter("seed"))))
```

See [SPEC.md](SPEC.md), [LAW.md](LAW.md), and [ROADMAP.md](ROADMAP.md).
