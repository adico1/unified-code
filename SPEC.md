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
    "state": "unknown" | "formed" | "valid" | "invalid",
}
```

## Canonical operation

```python
Thing = dict[str, object]
Part = Callable[[Thing], Thing]
```

Every public part must conform to `Part`.

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

## Conformance

A v0.1 implementation conforms when:

1. Public operations have one positional parameter.
2. The returned value remains a canonical thing.
3. Each axis adds exactly two opposed depths.
4. Spatial constructors produce 1D, 2D, and 3D interfaces correctly.
5. Verification exposes evidence and never silently converts unknown to
   false.
