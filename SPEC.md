# Unified Code Kernel Specification — Draft 0.1

## Status

Experimental. The purpose of v0.1 is to make the proposed laws executable
and falsifiable.

## Canonical thing

A thing is plain data with five fields:

```python
{
    "value": object,
    "depths": tuple[str, ...],
    "axes": tuple[tuple[str, str], ...],
    "evidence": tuple[str, ...],
    "state": "unknown" | "absent" | "false" | "formed" | "valid" | "invalid",
}
```

### States (L6)

| State | Meaning |
|---|---|
| `unknown` | Admitted but not yet classified by `letter` |
| `absent` | Classified as missing (`value is None`) |
| `false` | Classified as explicit false (`value is False`) |
| `formed` | Classified as a distinguished non-null, non-false value |
| `valid` | Passed dimensional verification |
| `invalid` | Failed verification or rejected non-canonical input |

Unknown, absent, false, and invalid are distinct. Verification may set
`valid` or `invalid` only. It must not convert unknown, absent, or false
into one another, and must never treat them as a boolean false.

## Canonical operation

```python
Thing = dict[str, object]
Part = Callable[[Thing], Thing]
```

Every public kernel part must accept one canonical thing and return one
canonical thing (L1). `letter` is not an exception: raw host values enter
only through the visible input boundary.

## Boundaries (L7)

Input/output are visible boundary parts, not hidden side effects:

| Part | Role |
|---|---|
| `inward` | Admit a host value into a canonical thing with state `unknown` |
| `outward` | Record emission intent in evidence; performs no host I/O |

`inward` is the only public operation allowed to accept a non-thing host
value; it always returns a canonical thing. `outward` accepts a thing and
returns a thing. Actual process printing, if any, is host-side after
`outward` has marked the effect.

## Depths

The initial ten depths are five opposed axes:

| Axis | Negative depth | Positive depth |
|---|---|---|
| time | beginning | end |
| value | good | bad |
| vertical | below | above |
| east-west | west | east |
| north-south | south | north |

Names identify orientation. They do not yet define coordinates, morality,
or application policy.

## Spatial dimensions

```text
1D = west/east
2D = west/east + south/north
3D = west/east + south/north + below/above
```

## Composition

Given parts `a`, `b`, and thing `x`:

```python
b(a(x))
```

means that `a` forms the inner result and `b` wraps or transforms that
result. Composition order is significant unless equivalence is proven.

Typical closed composition with boundaries:

```python
outward(world(verify(space(letter(inward(host_value))))))
```

## Conformance

A v0.1 implementation conforms when:

1. Public kernel parts have one positional parameter and, when given a
   canonical thing, return a canonical thing.
2. `letter` accepts a canonical thing, not a bare host value (L1).
3. Each axis adds exactly two opposed depths (L3, L4).
4. Spatial constructors produce 1D, 2D, and 3D interfaces correctly (L4).
5. Verification exposes evidence and never silently converts unknown,
   absent, or false into each other or into boolean false (L5, L6).
6. Input admission and output emission are represented by boundary parts
   with evidence; kernel parts do not hide I/O side effects (L7).
7. The core uses functions and plain data without required classes or
   inheritance (L8).

## Open design points

### `world()` and invalid things

`world()` currently appends `world:composed` even when the input thing has
`state` other than `valid` (including `invalid`). Existing tests preserve
this behavior.

The laws do **not** yet decide whether:

- `world` may mark any composition as a world, or
- `world` must require successful verification (`state == "valid"`), or
- `world` must reject or contain invalid input under a different state.

This remains an unresolved design point. Implementations must not treat
the current behavior as settled law until it is specified and tested as
conformance.
