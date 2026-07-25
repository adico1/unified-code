# UEM-16 Portable Primitive Registry — version 1

**Registry version:** `1`  
**Machine:** UEM-16  
**Spec:** UEM_SPEC.md 0.1  

Bytecode `APPLY` operands and `routes` values MUST name a primitive listed
here. Implementations MUST reject or fail unknown names as
`unknown-primitive` without opening a ticket.

Domain names MUST NOT appear as primitive names. Domain configuration is
data inside the program image only.

## Primitives (v1)

| Name | I/O | Purpose |
| --- | --- | --- |
| `identity` | pure | No-op |
| `letter` | pure | Classify formed vs skipped states; evidence `letter:*` |
| `mark_inward` | pure | Append `boundary:inward` |
| `require_source` | pure | Arity-1 source from host using image.source config |
| `accept_outward` | pure | Merge host-supplied outward_result into store |
| `eval_expression` | pure | Evaluate image.expression (+ bindings) |
| `merge_result` | pure | Write `_acc` to image.merge_key |
| `verify_result` | pure | Required field + evidence; fail → invalid, **no ticket** |
| `present_json` | pure | Ordered JSON presentation under store.presentation |
| `mark_part` | pure | Append part evidence from image.part_name |

## Expression operators (inside `eval_expression` only)

`literal`, `ref`, `field`, `object`, `count`, `require`, `as_int`,
`as_decimal`, `min_value`, `max_value`, `mul`, `add`, `sum_each`,
`quantize`, `decimal_str`, `str_len`, `line_count`, `word_count`,
`unique_casefold_word_count`.

Numeric: decimal strings for money-like fields; `quantize` uses
`ROUND_HALF_UP` when requested. Integers are JSON numbers without fraction.

## Versioning

- Bump registry version when adding/removing/changing primitive contracts.
- Older bytecode remains valid if it only uses still-listed names.
- Interpreters advertise registry version in CLI `--version`.
