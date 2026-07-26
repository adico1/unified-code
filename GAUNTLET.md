# L13 Complete Testing Gauntlet

**Verdict:** `fail`

Each dimension is scored separately. Never combined into one average.

| Dimension | Required | Actual | OK |
| --- | ---: | ---: | --- |
| `c_branches` | 100.0 | 78.19 (1115/1426) | NO |
| `c_functions` | 100.0 | 100.00 (76/76) | yes |
| `c_lines` | 100.0 | 100.00 (1567/1567) | yes |
| `error_ticket_paths` | 100.0 | 100.00 | yes |
| `event_routes` | 100.0 | 100.00 | yes |
| `fuzz_100k` | 100.0 | 100.00 | yes |
| `opcode_rejection_paths` | 100.0 | 100.00 | yes |
| `opcode_valid_paths` | 100.0 | 100.00 | yes |
| `opcodes` | 100.0 | 100.00 | yes |
| `physical_target_goldens` | 100.0 | 100.00 | yes |
| `primitive_registry` | 100.0 | 100.00 | yes |
| `python_branches` | 100.0 | 100.00 | yes |
| `python_c_differential` | 100.0 | 100.00 | yes |
| `python_statements` | 100.0 | 100.00 | yes |
| `required_mutations` | 100.0 | 100.00 | yes |
| `specification_requirements` | 100.0 | 100.00 | yes |
| `state_transitions` | 100.0 | 100.00 | yes |

## Rules

- No pragma/no-cover suppression
- Vendored third_party excluded from primary C score (reported separately if present)
- Tests/build scripts cannot inflate production coverage
- Assertions verify state, output, evidence, events, effects
- **Zero denominator is failure** (never report 100% of 0)

Generated in 97.1s.

## C branch ledger

- **Baseline (frozen):** `3a0bf81` → `c/tests/branch_baseline.json`
- Artifact: `c/tests/BRANCH_LEDGER.md` (+ `branch_ledger.json`, `branch_ledger_history.json`)
- Metric: gcov arc enumeration (same as L13 `c_branches`)
- `branches_hit` / `branches_total`: **1115 / 1426**
- Measurement: `missing_arcs_measured=311`, `in_ledger=311`, `unmapped=0`, `unclassified=0`
- Baseline conservation:
  - `baseline_open=311`
  - `resolved_by_test=0`
  - `removed_by_refactor=0`
  - `new_arcs=0`
  - `remapped_arcs=0` (informational)
  - `ambiguous_arcs=0` (must be 0)
  - `current_open=311`
  - equation holds: **True**
- L13 branch eligible: **False**
- Identity: `{file}:{line}:b{branch_id}` — do not rewrite baseline until all 311 original arcs are accounted for
- Generator: `python3 c/scripts/branch_ledger.py`

