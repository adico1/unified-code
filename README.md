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

See [docs/DEVELOPER_WORKFLOW.md](docs/DEVELOPER_WORKFLOW.md) for the full
sequence, scales (UC-0 through UC-4), and L9 measurement scope.

See [SPEC.md](SPEC.md), [LAW.md](LAW.md), and [ROADMAP.md](ROADMAP.md).
