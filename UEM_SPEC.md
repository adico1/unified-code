# Unified Event Machine — UEM-16 v0.1

## ROOT-authoritative generated surface

The accepted Stage-1 UEM contract deterministically generates the shared UEM
surface under [`generated/uem_surface/`](generated/uem_surface/):

```text
ROOT.seed
→ Stage-1 uem/contract.json
→ bootstrap/uem_surface.py
→ opcode + primitive registries
→ bytecode + canonical-result contracts
→ independent Python host boundary
→ independent C99 host boundary
→ POSIX/MCU/Wasm/Python target declarations
→ shared L11 vector declarations
```

The generated Python boundary invokes only `unified.machine.host`; the
generated C boundary invokes only `c/core`. Neither implementation generates,
embeds, invokes, or supplies expected results to the other. Both consume the
same ROOT-authoritative generated constants.

Generated target declarations begin as `declared-unverified` with
`support_claim=false`. Physical support remains governed by native goldens in
`c/targets/manifests/`; generation alone never creates a hardware claim.

The frozen five-file Stage-1 fixed point remains
`443671f1c8c752989489112d045c09ce7589abe03f9336f8a14a24edfdab8acf`.
The generated UEM surface has its own clean-room fixed point.

**Status:** foundation beneath Unified Code. Chip-neutral canonical machine.  
**Not claimed:** independent interpreters for x86-64, ARM64, RISC-V, or MCUs.

This phase proves a portable instruction set and reference Python implementation.
The existing Python generator remains; it is not replaced in v0.1.

## Versioning

| Field | Value |
| --- | --- |
| Machine family | UEM-16 |
| Spec version | 0.1 |
| Bytecode magic | `UEM\x16` (bytes `55 45 4D 16`) |
| Format version | `u16` big-endian `0x0001` |
| Program identity | SHA-256 of the full canonical bytecode blob |

Breaking opcode renumbering or encoding changes requires a new format version.
Decoders MUST reject unknown format versions and noncanonical encodings.

## Design constraints

No application-level jumps, branches, loops, classes, exceptions, or arbitrary
native calls. Interpreter residual control flow exists only inside named audited
primitives (dispatch table, queue walk, map/fold, expression eval) and is
counted explicitly.

Public machine API: every function accepts one Thing and returns one Thing.

Forbidden in machine/runtime source:

- `eval`, `exec`, `compile` of untrusted source
- dynamic `import` from bytecode
- reflection that loads arbitrary callables
- domain vocabulary (`invoice`, `text_stats`, `calculate_stats`, …)

## Machine Thing schema

```python
{
    "value": {
        "pc": int,                    # next instruction index
        "instructions": tuple,        # decoded (opcode_name, operand|None)
        "store": dict,                # named slots (plain data)
        "event": str | None,
        "event_id": str | None,
        "event_queue": tuple,         # FIFO of {name, id} or name
        "routes": dict,               # event name → primitive name
        "pending_primitive": str | None,
        "outward_request": dict | None,
        "outward_result": object | None,
        "ticket": dict | None,
        "halted": bool,
        "stop_reason": str | None,    # "stop" | "limit:*" | "fault" | ...
        "result": object | None,
        "limits": {
            "max_steps": int,
            "max_queue": int,
            "max_depth": int,
            "max_items": int,
            "max_memory": int,        # approximate JSON size of store+queue
            "max_output": int,
            "steps": int,
            "depth": int,
        },
        "image": dict,                # frozen program constants
        "program_sha256": str,
    },
    "depths": tuple,
    "axes": tuple,
    "evidence": tuple,                # ordered strings
    "state": "unknown"|"absent"|"false"|"formed"|"valid"|"invalid",
}
```

## Instruction schema

Symbolic:

```python
(opcode: str, operand: str | None)
```

Canonical program: ordered tuple of instructions. No labels. No jumps.

## Event schema

```python
{
    "name": str,          # e.g. "input.received"
    "id": str,            # deterministic identity for dedupe
}
```

Queue entries are either that object or a bare name (legacy decode expands
to `{name, id}` with id derived deterministically).

## Opcode table (16)

| Byte | Name | Operand | Semantics |
| --- | --- | --- | --- |
| `0x01` | `LOAD` | slot or `"host_input"` | Copy named input/image/host into `store["_acc"]` or named target if `slot<-source` form |
| `0x02` | `READ` | path | Read path from store root into `_acc` (`a.b.c` dotted) |
| `0x03` | `WRITE` | path | Write `_acc` into path under store |
| `0x04` | `DELETE` | path | Remove path under store |
| `0x05` | `EMIT` | event name | Set current event; append evidence `event:{name}` |
| `0x06` | `ENQUEUE` | event name or None | Enqueue current event (or operand name); FIFO |
| `0x07` | `DEQUEUE` | None | Pop queue head into current event; empty → `quiet` |
| `0x08` | `ROUTE` | routes slot | Resolve `routes[event]` → `pending_primitive`; unknown → invalid |
| `0x09` | `APPLY` | primitive or None | Apply `pending_primitive` or operand from registry |
| `0x0A` | `MAP` | config slot | Map primitive over list items (audited iteration) |
| `0x0B` | `FOLD` | config slot | Fold list items (audited iteration) |
| `0x0C` | `VERIFY` | config slot | Check invariants; fail → invalid, **no ticket** |
| `0x0D` | `TICKET` | None | Construct unrecovered-failure ticket (pure, redacted) |
| `0x0E` | `OUTWARD` | effect name | Request external effect; does not perform I/O itself |
| `0x0F` | `ACK` | None | Record external acknowledgement when external id present |
| `0x10` | `STOP` | reason or None | Halt; `stop_reason=stop`; final result from store |

Unknown opcode byte → invalid machine Thing (before execution).

## Deterministic queue ordering

- FIFO only.
- Enqueue appends to the right; dequeue removes from the left.
- Event id: `sha256(name|seq|salt)[:16]` unless provided.
- Duplicate `event_id` within one run is skipped with evidence
  `event:duplicate-skipped:{id}` (not re-applied).

## Primitive registry rules

1. Registry is a closed map: name → pure function `Thing → Thing`.
2. Names are generic (`eval_expression`, `letter`, `present_json`, …).
3. Domain names MUST NOT appear in machine source; callers pass config via
   `image` / store slots.
4. Unknown primitive name → invalid Thing (no ticket).
5. Primitives MUST NOT perform host I/O; only `OUTWARD` requests effects.
6. Expected validation failures set `state=invalid` and error fields; **no ticket**.
7. Unhandled machine/runtime fault → `TICKET` path (`ticket.open` semantics).

### Portable primitives (v0.1 minimum)

Required to run text statistics and invoice totals without domain hardcoding:

| Name | Role |
| --- | --- |
| `letter` | Classify null/false/value states |
| `mark_inward` | Evidence boundary:inward |
| `require_source` | Arity-1 source path/error codes from config |
| `eval_expression` | Domain-neutral expression AST evaluation |
| `merge_result` | Write expression result under configured key |
| `verify_result` | Required field + evidence membership |
| `present_json` | Ordered JSON object presentation |
| `mark_part` | Append part evidence marks from config |
| `state_transition` | Execute a generic seed-declared state transition |
| `identity` | No-op |

Expression operators (inside `eval_expression` only):  
`literal`, `ref`, `field`, `object`, `count`, `require`, `as_int`, `as_decimal`,
`min_value`, `max_value`, `mul`, `add`, `sum_each`, `quantize`, `decimal_str`,
`str_len`, `line_count`, `word_count`, `unique_casefold_word_count`.

## Failure and ticket semantics

| Case | Behavior | Ticket |
| --- | --- | --- |
| Expected validation / VERIFY fail | `state=invalid`, error in store | No |
| Unknown opcode / primitive / route | `state=invalid` | No |
| Unhandled machine fault | construct ticket (redacted) | Yes |
| `OUTWARD` without host fulfillment when required | invalid or host-driven | Policy: host supplies or STOP invalid |
| Limit exhaustion | `stop_reason=limit:*`, invalid | No (distinct from STOP) |

Ticket fields (after redaction):

```python
{
    "kind": "unhandled-exception",
    "operation": str,
    "error_type": str,
    "message": str,              # redacted
    "evidence": list,
    "correlation_id": str,       # deterministic
    "ticket_id": str,            # == correlation_id
    "occurred_at": str,
    "acked": bool,
}
```

Redaction runs before ticket fields and before any ticket evidence of secrets.
Persistence of tickets is an `OUTWARD` effect (`ticket.persist`), not implicit I/O
inside `TICKET`.

## Resource limits (defaults)

| Limit | Default |
| --- | --- |
| `max_steps` | 100_000 |
| `max_queue` | 10_000 |
| `max_depth` | 64 |
| `max_items` | 1_000_000 |
| `max_memory` | 8_000_000 (approx UTF-8 JSON chars of store+queue) |
| `max_output` | 2_000_000 |

Limit exhaustion evidence: `limit:steps`, `limit:queue`, `limit:depth`,
`limit:items`, `limit:memory`, `limit:output`.  
These MUST be distinct from normal `STOP` (`stop_reason=stop`).

## Stateful scalar profile

`state_transition` parses raw command arguments under one host-independent
profile:

- `integer` accepts only ASCII `-?(0|[1-9][0-9]*)`;
- its inclusive range is `-999999999999999` through `999999999999999`;
  this conservative 15-digit interval survives the vendored cJSON numeric
  representation and canonical serializer byte-for-byte;
- plus signs, surrounding whitespace, underscores, leading zeroes, Unicode
  digits, non-string inputs, and overflow are rejected as the argument's
  declared error;
- `non_empty` rejects the empty string and strings composed entirely of ASCII
  space, tab, LF, vertical tab, form feed, or carriage return;
- other Unicode whitespace is data, not whitespace, and is therefore non-empty.

Python generated applications, Python UEM, and C UEM MUST apply these rules
before guards and actions. Rejection leaves resource state unchanged.

## Binary encoding

Big-endian integers. No native host endianness.

```text
magic[4] = UEM\x16
version_u16 = 1
flags_u16 = 0
instr_count_u32
for i in 0..instr_count-1:
    opcode_u8          # 0x01..0x10 only
    tag_u8             # 0=none, 1=string
    if tag==1:
        len_u32
        utf8[len]      # well-formed UTF-8; no NUL requirement
image_len_u32
image_utf8[image_len]  # canonical JSON object, sort_keys, separators=(",",":")
```

**Canonicalization rules**

1. Opcode bytes exactly as table; no aliases.
2. Operand tag 0 when operand is None; tag 1 when string.
3. Empty string operand is allowed (len=0).
4. Image JSON: `json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))`.
5. UTF-8 only; decoder rejects invalid UTF-8.
6. No trailing bytes after image.
7. No compressed or alternate encodings.

**Program identity:** `sha256(bytecode_bytes).hexdigest()`.

**Decoder MUST reject:** wrong magic, bad version, unknown opcode, bad tag,
truncated, invalid UTF-8, trailing garbage, non-object image JSON,
noncanonical image (re-encode must match exactly).

## Execution model

1. `validate` bytecode → decoded program or invalid Thing.
2. `load` decoded program + host_input into machine Thing.
3. Loop `step` until `halted` or host must fulfill `OUTWARD`.
4. Host fulfills outward request by writing `outward_result` and clearing request,
   then continues `step`.
5. After `STOP`, further `step` yields invalid (`execution-after-stop`).

Evidence is append-only and ordered. Instruction evidence form:
`op:{OPCODE}` and optional `op:{OPCODE}:{operand}`.

## Compilation pipeline

```text
declaration → symbolic UEM program + image
           → canonical bytecode
           → verify decode
           → execute with host adapter
```

## Compatibility (v0.1 proof)

Compiling and executing the text-statistics and invoice-total declarations
through UEM must preserve:

- external JSON shape and key order on success
- states and error codes on failure
- required evidence marks (configured, not hard-coded domain logic)
- ticket behavior (validation → no ticket; unhandled fault → ticket)

## Gauntlet surface (v0.1)

Mutations that MUST be detected: opcode/operand mutation, truncation, appended
bytes, noncanonical encoding, invalid UTF-8, unknown primitive/opcode, route
omission, event reorder/duplicate/drop, missing verification, missing STOP,
execution after STOP, step/queue/depth/memory exhaustion, nondeterministic
output, swallowed machine fault, missing/duplicate/unredacted ticket, external
effect without OUTWARD, arbitrary native-code execution attempts.

## Measurements

Report: bytecode size, compile p95, decode/verify p95, execution p95, peak
machine state size, instruction count, event count, explicit control-flow
count by layer (machine core, primitives, compiler, tests, generator residual).

## Independent implementations

A second implementation (e.g. C99 under `c/`) must execute published
bytecode using **this specification** and golden vectors only — not by
translating the Python host. `APPLY` is bound to the versioned portable
registry (`c/REGISTRY.md` / registry version in the C CLI). Unknown
primitives are rejected.

**Chip support** is not claimed from compilation alone. A target passes
only when its executable runs the golden vectors with matching results.

## L11 — Cross-Host Equivalence

Conforming hosts produce identical **canonical observable results** for
valid programs and identical **rejections** for invalid encodings.

### Canonical result fields

| Field | Meaning |
| --- | --- |
| `canonical_version` | `1` |
| `registry_version` | portable primitive registry version |
| `unicode_profile` | e.g. `UEM-ASCII-1` |
| `program_sha256` | identity of bytecode |
| `state` | machine state |
| `stop_reason` | `stop` or `limit:*` or fault reason |
| `presentation` | `{text, exit_code}` or null |
| `stats` / `error` / `path` | domain-neutral outputs |
| `ticket` | redacted ticket object or null |
| `outward_log` | ordered outward requests |
| `events_emitted` / `events_dequeued` | ordered event names |
| `evidence` | ordered normalized marks (`op:NAME` not numeric) |
| `limit_hit` | null or limit kind |
| `steps` / `instruction_count` | counters |
| `reject` | decode/verify reject code when applicable |

### Unicode freeze (`UEM-ASCII-1`)

Until a later registry embeds full Unicode casefold data, case folding
maps only ASCII A–Z → a–z. Non-ASCII bytes/codepoints are unchanged.
Hosts MUST NOT use libc/`str.casefold` locale or OS Unicode for
equivalence-sensitive ops.

### Gauntlet requirements

1. Positive and negative vectors per opcode  
2. Combined program exercising all 16 opcodes  
3. Every registered primitive  
4. Full canonical output comparison (not selected fields only)  
5. Unknown primitives, bad routes, after-STOP, all resource limits  
6. Tickets: construct, redaction, dedupe, persistence boundary  
7. ASan and UBSan on the current tree  
8. Mutation/fuzz of bytecode  
9. Frozen Unicode profile  
10. Hardware execution before claiming x86-64/ARM64/RISC-V support

## Explicit non-goals (v0.1)

- Claiming multi-chip support without golden-vector execution on that chip
- Replacing Unified Code generator
- Network effects
- Mutable shared global state

## L12 — Physical-Target Conformance

### Support rule

A processor target is **supported** only when:

1. The executable runs on the **actual** target architecture (not QEMU-only for chip claims).
2. All unchanged golden vectors execute.
3. Canonical result bytes match the x86-64 reference.
4. Malformed bytecode is rejected identically.
5. Ticket and limit paths match.
6. Execution is deterministic across repeats.
7. A signed/retained target result manifest is stored under `c/targets/manifests/`.

### Host split

```text
c/core/        decoding, verification, execution, primitives
c/host/posix   files, stdout, CLI
c/host/wasm    Wasm entry (Wasm-host, not chip support)
c/host/mcu     UEM-MCU-1 bounded profile surface
```

### UEM-MCU-1

Fixed limits, no filesystem dependency in the intended embedding, OUTWARD
returns effect records to firmware. No MCU family is claimed without a
physical board golden pass.

### Status vocabulary

`native-pass` | `emulated-pass` | `compile-only` | `unavailable` | `native-fail`

## L13 — Complete Testing Gauntlet

See LAW.md L13. Emit `coverage.json` and `GAUNTLET.md` from
`unified.machine.l13.run_l13_gauntlet`. CI must fail on any dimension below 100%.
