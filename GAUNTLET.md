# L13 Complete Testing Gauntlet

**Verdict:** `fail`

Each dimension scored separately. Never averaged.

| Dimension | Required | Actual | OK |
| --- | ---: | ---: | --- |
| `c_branches` | 100 | None | **NO** |
| `c_functions` | 100 | None | **NO** |
| `c_lines` | 100 | None | **NO** |
| `error_ticket_paths` | 100 | 100.0 | yes |
| `event_routes` | 100 | 100.0 | yes |
| `fuzz_corpus` | 100 | 100.0 | yes |
| `opcode_rejection_paths` | 100 | 100.0 | yes |
| `opcode_valid_paths` | 100 | 100.0 | yes |
| `opcodes` | 100 | 100.0 | yes |
| `physical_target_goldens` | 100 | 100.0 | yes |
| `primitive_registry` | 100 | 100.0 | yes |
| `python_branches` | 100 | 85.5 | **NO** |
| `python_c_differential` | 100 | 100.0 | yes |
| `python_statements` | 100 | 91.56 | **NO** |
| `required_mutations` | 100 | 100.0 | yes |
| `specification_requirements` | 100 | 100.0 | yes |
| `state_transitions` | 100 | 100.0 | yes |

## Notes

- Dimensions never averaged
- Vendored C excluded from primary
- Harness modules omitted from Python production via .coveragerc
- Behavioral catalogs must be 100% before claiming L13 pass
- Code coverage dimensions still incomplete until every production line/branch is closed
