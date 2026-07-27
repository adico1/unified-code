# L13 Complete Testing Gauntlet

**Verdict:** `pass`

Each dimension is scored separately. Never combined into one average.

| Dimension | Required | Actual | OK |
| --- | ---: | ---: | --- |
| `c_branches` | 100.0 | 100.00 (1270/1270) | yes |
| `c_functions` | 100.0 | 100.00 (76/76) | yes |
| `c_lines` | 100.0 | 100.00 (1678/1678) | yes |
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

Generated in 33.5s.
