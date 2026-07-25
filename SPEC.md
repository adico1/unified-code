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
8. After a complete declaration, generation through filesystem publication
   completes in ≤ 1 second (1_000_000_000 ns) on ordinary local hardware
   for both project creation and feature addition, measured at p95 with
   all results valid (L9).
9. Generated domain and composition code use event-driven flow only; no
   explicit if/for/while/match/comprehensions (L10). Selection and
   iteration live only in audited primitives. Unhandled exceptions open
   a ticket via the outward ticket boundary.

## L9 — One-second construction

### Measured interval

Includes: validation, source generation, composition, structural
verification, filesystem writes, and result/evidence construction.

Excludes: human reasoning, human input time, dependency installation,
network operations, and running the generated program’s complete test suite.

### Clock boundary

Time is a host effect (L7). Public operations:

```python
def clock_start(thing) -> thing
def clock_end(thing) -> thing
```

Duration is recorded as an integer nanosecond count inside the thing.
Unknown, absent, or failed clock readings must not silently become
`false` or `valid`.

For L9 measurement of `uc new` / `uc add`, the closed interval is:

```text
clock_start
→ generation (validate → generate → verify_plan → write → outward evidence)
→ structural verification of the published project
→ iteration verdict and evidence construction
→ clock_end
```

Iteration index and operation name are fields of the canonical thing, not
extra function parameters (L1).

### Benchmark

```bash
uc benchmark
uc benchmark --iterations 20
```

Reports for each of `new` and `add`:

```text
iterations
minimum_ns
median_ns
p95_ns
maximum_ns
limit_ns = 1_000_000_000
verdict
```

L9 PASS only when:

```text
new p95_ns <= 1_000_000_000
add p95_ns <= 1_000_000_000
all generated results are valid
```

Authoritative L9 measurement is local ordinary hardware. CI verifies
benchmark logic; cloud-runner wall time is not the authority for L9.

## L10 — Event-Driven Flow

### Application surface

Generated `parts.py` and `compose.py` must contain **zero** of:

```text
If, For, While, Match, ListComp, SetComp, DictComp, GeneratorExp
Try used as control-flow (except inside audited event_runtime)
Recursion used as a loop substitute
```

Routing is data (`ROUTES` / `EVENTS` dict). Handlers are `Thing → Thing`.
Every event appends ordered evidence. Unknown events produce an explicit
invalid Thing (`unknown-event`). Event ordering is deterministic (FIFO
queue processed by `until_quiet`).

### Audited primitives (where control flow remains)

| Primitive | Role |
| --- | --- |
| `emit` | set event + evidence |
| `enqueue` / `dequeue` | deterministic queue |
| `route` | table lookup |
| `until_quiet` | process until queue empty |
| `map_event` / `fold_event` | collection iteration |
| `call_part` | Part invoke; unhandled → ticket path |
| `require_str_field` / `identity_part` | domain guards without domain if |
| `run_expression` | expression evaluation (expr_runtime) |
| `open_ticket` / `preserve_for_retry` / `ack_ticket` | ticket boundary |

Moving an `if` from `parts.py` into a non-audited generated helper is a
**conformance failure**. The primitives above are the only permitted homes
for selection and iteration in generated applications.

### Exception policy

```text
Expected domain rejection:
    validation.failed → reject
    No ticket is opened.

Recoverable operational failure:
    operation.failed → configured recovery handler
    Recovery evidence is recorded.

Unrecoverable or unhandled exception:
    exception.raised → ticket.open → processing.failed
```

Ticket rules: one failure one ticket; redact secrets; outbox when no
provider; ack only after external id; delivery failure preserves outbox.

### Control-flow measurement report

Gauntlets and benchmarks report explicit control-flow counts separately for:

```text
framework kernel
generator
generated runtime (event_runtime, expr_runtime, boundary)
domain parts
compose
tests
```

Do not claim control flow was eliminated if it was merely relocated.

## Host-edge model (resolved)

**Model 2 — fewer exceptions:**

1. `parse_host_argv` and `present_result` are public Parts: one thing in,
   one thing out. Presentation text and exit code live inside
   `thing["value"]["presentation"]`.
2. `host_main` is **not** a Unified Code operation. It is the OS process
   edge only: it writes stdout and sets the process exit status from the
   thing after `program(...)`.
3. `host_main` must never appear in nested domain composition or in the
   discovered public Part surface for L1 checks.

Kernel/domain Parts remain strictly Thing→Thing with no pair returns.

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
