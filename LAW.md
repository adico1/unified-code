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

## L10 — Event-Driven Flow

Application and generated code contain no explicit loops or branching.
A Thing changes through named events, declarative routes, and
compositional handlers. Each handler is `Thing → Thing`.

```python
EVENTS = {
    "input.received": validate,
    "input.valid": calculate,
    "input.invalid": reject,
    "calculation.complete": present,
}

def handle(thing):
    return EVENTS[thing["event"]](thing)
```

### Required transformation

| Current construct      | Unified replacement                                         |
| ---------------------- | ----------------------------------------------------------- |
| `if / elif / else`     | predicate emits an event → route table selects handler      |
| `for / while`          | collection emits item events → deterministic fold/reduction |
| `try / except`         | operation emits success/failure event                       |
| Boolean control flags  | explicit states or events                                   |
| Function orchestration | event pipeline                                              |
| Nested branching       | named route composition                                     |
| Repeated polling       | external event source                                       |

### Two conformance levels

* **Application conformance:** no explicit loops or conditionals in
  generated domain/application code (`parts.py`, `compose.py`).
* **Kernel conformance:** iteration and routing exist only as *audited*
  deterministic primitives. **Audited** means: formal contract + direct
  tests for termination, ordering, duplication, and failure — not merely
  a name.

Hiding `if`/`for` inside another generated helper does **not** remove
imperative control flow unless that helper is contract-tested.

Current achievement (precise):

> Generated domain logic and composition are event-driven, while
> imperative control flow is confined to named runtime primitives and
> boundaries.

It is **not** accurate to call the entire system or generator fully
event-driven while generated runtime and the generator still contain
large explicit control-flow counts.

### Exception and ticket policy

| Case | Route | Ticket |
| --- | --- | --- |
| Expected domain rejection | `validation.failed` → reject | No |
| Recoverable operational failure | `operation.failed` → recovery handler | No (unless policy says so) |
| Unrecoverable / unhandled exception | see ticket chain below | Yes |

Ticket chain (construct pure; persist outward):

```text
exception.unhandled
→ ticket.construct          (construct_ticket — pure, redacts first)
→ ticket.persist.requested
→ outward_ticket_store      (atomic write; named outward boundary)
→ ticket.persisted
→ processing.failed
```

Persist failure:

```text
ticket.persist.failed → emergency result
(never recursively constructs another ticket)
```

Ticket identity is the deterministic `correlation_id` derived from the
failure material after redaction. One failure → one ticket. Restart
reloads unacknowledged tickets via `reload_unacked_tickets`.
Acknowledgement requires a real non-empty external ticket id.

## L11 — Cross-Host Equivalence

Every conforming UEM host must produce the same canonical observable
result for every valid program/input pair and the same canonical
rejection for every invalid byte sequence.

Canonical fields include state, presentation, evidence (normalized),
events, tickets, outward_log, limit_hit, and program identity.
Unicode text ops use frozen profile `UEM-ASCII-1` (ASCII A–Z only).
A CPU target is supported only after its executable runs golden vectors.
