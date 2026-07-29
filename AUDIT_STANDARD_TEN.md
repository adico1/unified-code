# Standard Ten Repository Audit

## Separate conformance verdicts

**Milestone 1 historical task-ledger checkpoint:** `superseded`

- Public command: `uc unfold seed/declarations/task_ledger.json --output /tmp/uc-task-ledger --verify --run`
- Its original Python/C claim measured canonical payload transport, not independent application transitions. Milestone 1.1 corrects that proof.

**Milestone 1.1 seed-defined stateful conformance:** `pass`

- Independent declarations: `seed/declarations/task_ledger.json` and `seed/declarations/score_board.json`
- Application schema, commands, validation, transitions, results, errors, persistence identity, composition, and scenarios originate in JSON.
- Python and C independently execute the same seed-defined transition program over the same pre-state, command, and raw arguments.
- `scripts/check_stateful_overfit.py` rejects application vocabulary in generic generation and UEM runtime source.
- Contextual mutation rejects `command == "add"` in stateful runtime while preserving the registered expression operator.
- Generated Python, Python UEM, and C UEM implement the frozen scalar profile; L11 covers accepted, rejected, minimum, maximum, overflow, Unicode-digit, and whitespace vectors.
- Static application-vocabulary leaks: `0`

**Milestone 2 self-hosting conformance:** `fail` (`open`, non-blocking)

The repository-wide figures and gaps below measure only the root-seed fixed-point bootstrap. They do not mean that the application generator failed.

**Repository self-hosting verdict:** `fail`
**standard_version:** TEN-1
**seed_sha256:** `9b145882d8aaa29dfec413ce78e72e86998349a5d7e63118b0daf361b26d25c2`
**files classified:** 418
**illegal provenance (not in allowed five classes):** 236
**OOP class files:** 0
**open standard.gap tickets:** 6

## Non-fallback law

Conventional development is not an authorized fallback. Gaps below are `standard.gap` — not invitations to implement with OOP, handwritten app logic, or dual interface stacks.

## Open gaps

- **gap.seed-expresses-full-framework** (rule 3): UEM machine, generator, and framework modules are not yet fully expressed as seed package bodies; currently handwritten under unified/.
- **gap.no-app-control-flow-in-host** (rule 6): Python/C UEM hosts still use imperative control flow (required for physical boundary execution until seed can emit hosts).
- **gap.declarations-as-python** (rule 4): Application declarations live as .py modules with Python syntax; must be pure JSON under seed/declarations/.
- **gap.dual-host-not-single-machine-surface** (rule 7): Python and C interpreters are parallel implementations; Standard Ten requires one UEM with hosts as boundaries only. Semantic parity is proven (L11) but structure is dual-impl.
- **gap.generated-tests-and-docs** (rule 10): Tests and documentation are handwritten, not generated from seed/declaration.
- **gap.clean-room-full-tree** (rule 3): Clean-room regeneration cannot yet emit the full repository from seed alone.

## OOP violations

- (none)

## Provenance summary

| Class | Count |
| --- | ---: |
| `evidence` | 7 |
| `external-vendored` | 4 |
| `generated` | 125 |
| `handwritten-pending` | 236 |
| `physical-host-boundary` | 16 |
| `seed` | 30 |

## Clean-room status

Full-tree clean-room regeneration is **not** claimed. See `gap.clean-room-full-tree`. Partial regeneration of seed-locked UEM artifacts is exercised by `scripts/clean_room_ten.sh`.

## File table (path · class · compliance · sha256[:16])

- `.coverage` · `evidence` · `ok` · `0582dadf4a76f6ed`
- `.coveragerc` · `handwritten-pending` · `standard.gap` · `f4c1eac25e83d766`
- `.github/workflows/test.yml` · `handwritten-pending` · `standard.gap` · `224c02a74cf42f1d`
- `.gitignore` · `handwritten-pending` · `standard.gap` · `699c693cc407b221`
- `APPLICATION_ASSEMBLY.md` · `handwritten-pending` · `standard.gap` · `8bacd4ab1df79455`
- `AUDIT_STANDARD_TEN.md` · `evidence` · `ok` · `8f97efff3c9b7adf`
- `GAUNTLET.md` · `evidence` · `ok` · `0fa0d5bc6bb62286`
- `LAW.md` · `handwritten-pending` · `standard.gap` · `774f91fa24ce4acd`
- `LICENSE` · `handwritten-pending` · `standard.gap` · `af6b910929ec375c`
- `MANIFESTATION.md` · `handwritten-pending` · `standard.gap` · `15efdca893c191c3`
- `PROVENANCE_MANIFEST.json` · `evidence` · `ok` · `23cfc30db9f26b83`
- `README.md` · `handwritten-pending` · `standard.gap` · `074c929f30e14ee5`
- `ROADMAP.md` · `handwritten-pending` · `standard.gap` · `cec16f240821e25c`
- `ROOT_CONVERGENCE.md` · `handwritten-pending` · `standard.gap` · `a2a6a6142608d173`
- `SPEC.md` · `handwritten-pending` · `standard.gap` · `770c5f67b0bc7824`
- `STAGE0.md` · `handwritten-pending` · `standard.gap` · `9e2bae9dd4ed3f3a`
- `STAGE1.md` · `handwritten-pending` · `standard.gap` · `2e0f4ae22335666b`
- `STAGE1_FIXED_POINT.md` · `handwritten-pending` · `standard.gap` · `6316896f841a697b`
- `STANDARD_TEN.md` · `seed` · `ok` · `d7152599e81fa3e1`
- `THING_V2.md` · `handwritten-pending` · `standard.gap` · `da567f98a7b53f54`
- `UEM_SPEC.md` · `handwritten-pending` · `standard.gap` · `63d2020f5a77ef5f`
- `VERIFY_FLOW.md` · `handwritten-pending` · `standard.gap` · `a8a4df82c4ef96ad`
- `artifacts/uem/invoice_total/program.symbolic.json` · `generated` · `ok` · `a1899fe0c2f6ac40`
- `artifacts/uem/invoice_total/program.symbolic.json.stamp.json` · `generated` · `ok` · `4fc5f5b144118ff1`
- `artifacts/uem/invoice_total/program.uem` · `generated` · `ok` · `cf2a87a8219f26e5`
- `artifacts/uem/invoice_total/program.uem.stamp.json` · `generated` · `ok` · `702ee448c1fadc83`
- `artifacts/uem/text_stats_v2/program.symbolic.json` · `generated` · `ok` · `2813f009eccd6cd9`
- `artifacts/uem/text_stats_v2/program.symbolic.json.stamp.json` · `generated` · `ok` · `1f90c6814be8e951`
- `artifacts/uem/text_stats_v2/program.uem` · `generated` · `ok` · `b625f4a2104df5a4`
- `artifacts/uem/text_stats_v2/program.uem.stamp.json` · `generated` · `ok` · `9bf8e23d85d2ba42`
- `bootstrap/fixed_point.py` · `handwritten-pending` · `standard.gap` · `d018b708d67cdde1`
- `bootstrap/stage0.py` · `handwritten-pending` · `standard.gap` · `d1ba66af02b606e2`
- `bootstrap/uem_surface.py` · `handwritten-pending` · `standard.gap` · `3c9101d9907c1640`
- `bootstrap/verification_surface.py` · `handwritten-pending` · `standard.gap` · `fad8ab346881242f`
- `c/.gitignore` · `handwritten-pending` · `standard.gap` · `2dc3b312a4902f53`
- `c/Makefile` · `handwritten-pending` · `standard.gap` · `1c23d3b0fc4dbf85`
- `c/README.md` · `handwritten-pending` · `standard.gap` · `84a0d2f879ecac82`
- `c/REGISTRY.md` · `handwritten-pending` · `standard.gap` · `e2c03426cd04c88c`
- `c/core/alloc.c` · `physical-host-boundary` · `ok` · `205c11e59669f1ed`
- `c/core/alloc.h` · `physical-host-boundary` · `ok` · `bfa89ba51b39d5d4`
- `c/core/decimal.c` · `physical-host-boundary` · `ok` · `b719a7691e18c0e8`
- `c/core/decimal.h` · `physical-host-boundary` · `ok` · `a9ca485106343638`
- `c/core/decode.c` · `physical-host-boundary` · `ok` · `ad682987fa8f0781`
- `c/core/expr.c` · `physical-host-boundary` · `ok` · `4429acabdcabad15`
- `c/core/machine.c` · `physical-host-boundary` · `ok` · `818f8cdada11cbe9`
- `c/core/machine_internal.h` · `physical-host-boundary` · `ok` · `388a52887aa8ebe9`
- `c/core/primitives.c` · `physical-host-boundary` · `ok` · `abcf79c2707607c2`
- `c/core/stateful.c` · `physical-host-boundary` · `ok` · `aa2b4c2cf8b7f58e`
- `c/host/mcu/mcu_host.c` · `physical-host-boundary` · `ok` · `8d18055f3f71ec77`
- `c/host/mcu/uem_mcu.h` · `physical-host-boundary` · `ok` · `ba4469916eabbd40`
- `c/host/posix/main.c` · `physical-host-boundary` · `ok` · `78145a6ea38475a3`
- `c/host/wasm/main.c` · `physical-host-boundary` · `ok` · `4a9da23c975b1e02`
- `c/include/uem.h` · `physical-host-boundary` · `ok` · `7d24711c97c4c49f`
- `c/scripts/branch_ledger.py` · `handwritten-pending` · `standard.gap` · `188b4ce9d85cec1b`
- `c/scripts/build_cross.sh` · `handwritten-pending` · `standard.gap` · `177d91a9e6f2587a`
- `c/scripts/diff_py_c.sh` · `handwritten-pending` · `standard.gap` · `909cca5cc70ed1a1`
- `c/scripts/fuzz_bytecode.py` · `handwritten-pending` · `standard.gap` · `c6588410a65b5a72`
- `c/scripts/fuzz_l12.py` · `handwritten-pending` · `standard.gap` · `94138743da31ceff`
- `c/scripts/gcov_arcs.py` · `handwritten-pending` · `standard.gap` · `35102b4156c2eb38`
- `c/scripts/gen_golden.sh` · `handwritten-pending` · `standard.gap` · `3714c03feb458f02`
- `c/scripts/run_l11_full.sh` · `handwritten-pending` · `standard.gap` · `7d2cc34998478d50`
- `c/scripts/run_l12_report.py` · `handwritten-pending` · `standard.gap` · `59a553ecb2c3b355`
- `c/scripts/run_tests.sh` · `handwritten-pending` · `standard.gap` · `aaf230b1f4c73ece`
- `c/targets/manifests/l12_report_x86_64.json` · `evidence` · `ok` · `ba140efcd572d4c1`
- `c/tests/BRANCH_LEDGER.md` · `handwritten-pending` · `standard.gap` · `64fbcd45154a4a28`
- `c/tests/branch_baseline.json` · `handwritten-pending` · `standard.gap` · `b6e5feed17b09ebf`
- `c/tests/branch_ledger.json` · `handwritten-pending` · `standard.gap` · `8aef627633bf693d`
- `c/tests/branch_ledger_history.json` · `handwritten-pending` · `standard.gap` · `798c846d4a40e2f4`
- `c/tests/core_coverage_harness.c` · `handwritten-pending` · `standard.gap` · `95989eaac5381d96`
- `c/tests/coverage_vectors/amiss.uem` · `handwritten-pending` · `standard.gap` · `c48edea268bf8191`
- `c/tests/coverage_vectors/assert_badimgutf8.uem` · `handwritten-pending` · `standard.gap` · `e1a25cd1b00272b0`
- `c/tests/coverage_vectors/assert_esc.uem` · `handwritten-pending` · `standard.gap` · `bb4d815983e0bd5c`
- `c/tests/coverage_vectors/assert_float.uem` · `handwritten-pending` · `standard.gap` · `2806fbd4625fb180`
- `c/tests/coverage_vectors/assert_load.uem` · `handwritten-pending` · `standard.gap` · `98243bb061a6ee98`
- `c/tests/coverage_vectors/assert_nostop.uem` · `handwritten-pending` · `standard.gap` · `469ecde8632675ac`
- `c/tests/coverage_vectors/assert_nullimg.uem` · `handwritten-pending` · `standard.gap` · `146af03abdd2e69d`
- `c/tests/coverage_vectors/assert_quiet.uem` · `handwritten-pending` · `standard.gap` · `59f8571ea7ec862f`
- `c/tests/coverage_vectors/assert_tick.uem` · `handwritten-pending` · `standard.gap` · `16078838cacb9754`
- `c/tests/coverage_vectors/assert_trail.uem` · `handwritten-pending` · `standard.gap` · `729c0c837cb14c06`
- `c/tests/coverage_vectors/assert_truncimg.uem` · `handwritten-pending` · `standard.gap` · `1d45a235d360dc39`
- `c/tests/coverage_vectors/assert_unkprim.uem` · `handwritten-pending` · `standard.gap` · `e25af0291db25f51`
- `c/tests/coverage_vectors/ctrl.uem` · `handwritten-pending` · `standard.gap` · `42a8679ba19ac9f6`
- `c/tests/coverage_vectors/enq.uem` · `handwritten-pending` · `standard.gap` · `c89c4879c6d57139`
- `c/tests/coverage_vectors/esc.uem` · `handwritten-pending` · `standard.gap` · `770a77dcd71bbc97`
- `c/tests/coverage_vectors/ev.uem` · `handwritten-pending` · `standard.gap` · `99c12d721cf71c77`
- `c/tests/coverage_vectors/img.uem` · `handwritten-pending` · `standard.gap` · `6c8a68ca3a040f33`
- `c/tests/coverage_vectors/limg.uem` · `handwritten-pending` · `standard.gap` · `6c8a68ca3a040f33`
- `c/tests/coverage_vectors/mb_0.uem` · `handwritten-pending` · `standard.gap` · `af7319705bdacabc`
- `c/tests/coverage_vectors/mb_1.uem` · `handwritten-pending` · `standard.gap` · `1cbe6dcd4030a933`
- `c/tests/coverage_vectors/mb_2.uem` · `handwritten-pending` · `standard.gap` · `62c29796c1e68484`
- `c/tests/coverage_vectors/mb_3.uem` · `handwritten-pending` · `standard.gap` · `d8084da0755824dd`
- `c/tests/coverage_vectors/mf.uem` · `handwritten-pending` · `standard.gap` · `adee76bf05e80312`
- `c/tests/coverage_vectors/nostop.uem` · `handwritten-pending` · `standard.gap` · `8c0b1fcc0f0ce976`
- `c/tests/coverage_vectors/nostop2.uem` · `handwritten-pending` · `standard.gap` · `469ecde8632675ac`
- `c/tests/coverage_vectors/quiet.uem` · `handwritten-pending` · `standard.gap` · `9cad52ff87c6de10`
- `c/tests/coverage_vectors/tick.uem` · `handwritten-pending` · `standard.gap` · `16078838cacb9754`
- `c/tests/coverage_vectors/trail.uem` · `handwritten-pending` · `standard.gap` · `54416af308c773be`
- `c/tests/coverage_vectors/uroute.uem` · `handwritten-pending` · `standard.gap` · `57fabd7bebcb2e1e`
- `c/tests/coverage_vectors/utf4.uem` · `handwritten-pending` · `standard.gap` · `a4a2e5fea36adf16`
- `c/tests/coverage_vectors/v000.uem` · `handwritten-pending` · `standard.gap` · `b41edab3ba1c6702`
- `c/tests/coverage_vectors/v001.uem` · `handwritten-pending` · `standard.gap` · `c3f7572d20a98941`
- `c/tests/coverage_vectors/v002.uem` · `handwritten-pending` · `standard.gap` · `7717b5c1d3bfb1d2`
- `c/tests/coverage_vectors/v003.uem` · `handwritten-pending` · `standard.gap` · `449193c640d36c69`
- `c/tests/coverage_vectors/v004.uem` · `handwritten-pending` · `standard.gap` · `ff7286484b49544d`
- `c/tests/coverage_vectors/v005.uem` · `handwritten-pending` · `standard.gap` · `e263acfdc98cac7a`
- `c/tests/coverage_vectors/v006.uem` · `handwritten-pending` · `standard.gap` · `dd67e2b378664f1d`
- `c/tests/coverage_vectors/v007.uem` · `handwritten-pending` · `standard.gap` · `3e2791f78c8a4a93`
- `c/tests/coverage_vectors/v008.uem` · `handwritten-pending` · `standard.gap` · `16078838cacb9754`
- `c/tests/coverage_vectors/v009.uem` · `handwritten-pending` · `standard.gap` · `0f19e18ad97ebfe5`
- `c/tests/coverage_vectors/v010.uem` · `handwritten-pending` · `standard.gap` · `416ac53eae35899b`
- `c/tests/coverage_vectors/v011.uem` · `handwritten-pending` · `standard.gap` · `b625f4a2104df5a4`
- `c/tests/coverage_vectors/v012.uem` · `handwritten-pending` · `standard.gap` · `cf2a87a8219f26e5`
- `c/tests/coverage_vectors/wrd.uem` · `handwritten-pending` · `standard.gap` · `c902d659adcea9df`
- `c/tests/fuzz_corpus/seed_0000.uem` · `handwritten-pending` · `standard.gap` · `b625f4a2104df5a4`
- `c/tests/fuzz_corpus/seed_0001.uem` · `handwritten-pending` · `standard.gap` · `b625f4a2104df5a4`
- `c/tests/fuzz_corpus/seed_0002.uem` · `handwritten-pending` · `standard.gap` · `cf2a87a8219f26e5`
- `c/tests/fuzz_corpus/seed_0003.uem` · `handwritten-pending` · `standard.gap` · `2ea6e97a6a0c876f`
- `c/tests/fuzz_corpus/seed_0004.uem` · `handwritten-pending` · `standard.gap` · `9beeba5b4c4b4d6d`
- `c/tests/fuzz_corpus/seed_0005.uem` · `handwritten-pending` · `standard.gap` · `0bc7649914086bc7`
- `c/tests/fuzz_corpus/seed_0006.uem` · `handwritten-pending` · `standard.gap` · `2ea6e97a6a0c876f`
- `c/tests/fuzz_corpus/seed_0007.uem` · `handwritten-pending` · `standard.gap` · `af886cc0f7d670b2`
- `c/tests/fuzz_corpus/seed_0008.uem` · `handwritten-pending` · `standard.gap` · `2ea6e97a6a0c876f`
- `c/tests/fuzz_corpus/seed_0009.uem` · `handwritten-pending` · `standard.gap` · `62b0807e71ac7988`
- `c/tests/fuzz_corpus/seed_0010.uem` · `handwritten-pending` · `standard.gap` · `1eae99efa61aa7cb`
- `c/tests/fuzz_corpus/seed_0011.uem` · `handwritten-pending` · `standard.gap` · `cf15c41706455dcb`
- `c/tests/fuzz_corpus/seed_0012.uem` · `handwritten-pending` · `standard.gap` · `4c2d094543d01aac`
- `c/tests/fuzz_corpus/seed_0013.uem` · `handwritten-pending` · `standard.gap` · `62b0807e71ac7988`
- `c/tests/fuzz_corpus/seed_0014.uem` · `handwritten-pending` · `standard.gap` · `e1809420d55cd1e0`
- `c/tests/fuzz_corpus/seed_0015.uem` · `handwritten-pending` · `standard.gap` · `ab661832955529d3`
- `c/tests/fuzz_corpus/seed_0016.uem` · `handwritten-pending` · `standard.gap` · `2c2f44bbbddabe57`
- `c/tests/fuzz_corpus/seed_0017.uem` · `handwritten-pending` · `standard.gap` · `4339951a2998dd8b`
- `c/tests/fuzz_corpus/seed_0018.uem` · `handwritten-pending` · `standard.gap` · `3b7d935d8ee4c5a9`
- `c/tests/fuzz_corpus/seed_0019.uem` · `handwritten-pending` · `standard.gap` · `316197b478c46ad3`
- `c/tests/fuzz_corpus/seed_0020.uem` · `handwritten-pending` · `standard.gap` · `acfeffdbfd992f77`
- `c/tests/fuzz_corpus/seed_0021.uem` · `handwritten-pending` · `standard.gap` · `2ea6e97a6a0c876f`
- `c/tests/fuzz_corpus/seed_0022.uem` · `handwritten-pending` · `standard.gap` · `b41edab3ba1c6702`
- `c/tests/fuzz_corpus/seed_0023.uem` · `handwritten-pending` · `standard.gap` · `2ea6e97a6a0c876f`
- `c/tests/fuzz_corpus/seed_0024.uem` · `handwritten-pending` · `standard.gap` · `32a66b77075a5db9`
- `c/tests/fuzz_corpus/seed_0025.uem` · `handwritten-pending` · `standard.gap` · `579089704d687ffb`
- `c/tests/fuzz_corpus/seed_0026.uem` · `handwritten-pending` · `standard.gap` · `2ea6e97a6a0c876f`
- `c/tests/fuzz_corpus/seed_0027.uem` · `handwritten-pending` · `standard.gap` · `9a60e98b37021cb4`
- `c/tests/fuzz_corpus/seed_0028.uem` · `handwritten-pending` · `standard.gap` · `92b85cddfde8ca31`
- `c/tests/fuzz_corpus/seed_0029.uem` · `handwritten-pending` · `standard.gap` · `62b0807e71ac7988`
- `c/tests/fuzz_corpus/seed_0030.uem` · `handwritten-pending` · `standard.gap` · `88f1f540f45ef54c`
- `c/tests/fuzz_corpus/seed_0031.uem` · `handwritten-pending` · `standard.gap` · `6a41cb5394238eb8`
- `c/tests/fuzz_corpus/seed_0032.uem` · `handwritten-pending` · `standard.gap` · `49a1d3b8256076ba`
- `c/tests/fuzz_corpus/seed_0033.uem` · `handwritten-pending` · `standard.gap` · `2ea6e97a6a0c876f`
- `c/tests/fuzz_corpus/seed_0034.uem` · `handwritten-pending` · `standard.gap` · `2ea6e97a6a0c876f`
- `c/tests/golden/inv_basic.json` · `handwritten-pending` · `standard.gap` · `ae42acc75d6443ed`
- `c/tests/golden/inv_empty_items.json` · `handwritten-pending` · `standard.gap` · `0fed4880fd5e2152`
- `c/tests/golden/inv_half_cent.json` · `handwritten-pending` · `standard.gap` · `782a3cd0d811385b`
- `c/tests/golden/inv_reject_qty.json` · `handwritten-pending` · `standard.gap` · `5fa4aca0c9ccbe95`
- `c/tests/golden/ts_empty.json` · `handwritten-pending` · `standard.gap` · `8e548d089277a0f6`
- `c/tests/golden/ts_gogo.json` · `handwritten-pending` · `standard.gap` · `762025af4f74450e`
- `c/tests/vectors/bad_magic.uem` · `handwritten-pending` · `standard.gap` · `0ff64a815f69820e`
- `c/tests/vectors/trailing.uem` · `handwritten-pending` · `standard.gap` · `88ab7520c9152174`
- `c/tests/vectors/truncated.uem` · `handwritten-pending` · `standard.gap` · `33870149c489e383`
- `c/tests/vectors/unknown_opcode.uem` · `handwritten-pending` · `standard.gap` · `9bef076d238d33a9`
- `c/third_party/cJSON.c` · `external-vendored` · `ok` · `75c51de8fa40ac9d`
- `c/third_party/cJSON.h` · `external-vendored` · `ok` · `0578cc29132912ed`
- `c/third_party/sha256.c` · `external-vendored` · `ok` · `7512aca9136ce6e2`
- `c/third_party/sha256.h` · `external-vendored` · `ok` · `ee296ea123f062e6`
- `contract_report.json` · `handwritten-pending` · `standard.gap` · `7805a99ab3fa9825`
- `contract_status.json` · `handwritten-pending` · `standard.gap` · `3ed75edf9b64810f`
- `coverage.json` · `evidence` · `ok` · `b6130a1054645415`
- `coverage_py.json` · `evidence` · `ok` · `f6277200dfe9e536`
- `docs/DEVELOPER_WORKFLOW.md` · `handwritten-pending` · `standard.gap` · `972a9832bc0260a7`
- `examples/declarations/invoice_total.json` · `handwritten-pending` · `standard.gap` · `1a0479e011592752`
- `examples/declarations/invoice_total.py` · `handwritten-pending` · `standard.gap` · `d0cb833aace2a12a`
- `examples/declarations/text_stats_program.json` · `handwritten-pending` · `standard.gap` · `c8c1c8f23b4e780a`
- `examples/declarations/text_stats_program.py` · `handwritten-pending` · `standard.gap` · `d9d565c596a5efdd`
- `examples/declarations/text_stats_v2.json` · `handwritten-pending` · `standard.gap` · `ac4a679c4e32180f`
- `examples/declarations/text_stats_v2.py` · `handwritten-pending` · `standard.gap` · `0c083c7704d22e8d`
- `examples/one_dimension.py` · `handwritten-pending` · `standard.gap` · `48d90d21a1e77ced`
- `examples/three_dimensions.py` · `handwritten-pending` · `standard.gap` · `a5bc88a92e9fcf54`
- `examples/two_dimensions.py` · `handwritten-pending` · `standard.gap` · `a6eec3842bbbe930`
- `generated/uem_surface/__init__.py` · `generated` · `ok` · `2cbd00d2f1b1304a`
- `generated/uem_surface/c/host/generated/uem_generated_host.c` · `generated` · `ok` · `37c9e4e3d6e53740`
- `generated/uem_surface/c/host/generated/uem_generated_host.h` · `generated` · `ok` · `a8eca690e3e013d0`
- `generated/uem_surface/c/include/uem_generated_surface.h` · `generated` · `ok` · `23fe24fd5754156b`
- `generated/uem_surface/registry/opcodes.json` · `generated` · `ok` · `18f86a8df391c413`
- `generated/uem_surface/registry/primitives.json` · `generated` · `ok` · `09eba5721c0a9842`
- `generated/uem_surface/schema/canonical-result.json` · `generated` · `ok` · `09399887210475bc`
- `generated/uem_surface/spec/uem.json` · `generated` · `ok` · `c1b1979da0e7e228`
- `generated/uem_surface/targets/mcu.json` · `generated` · `ok` · `e333cff90ed789a0`
- `generated/uem_surface/targets/posix.json` · `generated` · `ok` · `6e4d45e136ae9eef`
- `generated/uem_surface/targets/python-host.json` · `generated` · `ok` · `8753cca71c0bff48`
- `generated/uem_surface/targets/wasm.json` · `generated` · `ok` · `c1f0ec041e16fac0`
- `generated/uem_surface/uem-surface-manifest.json` · `generated` · `ok` · `6022d70873baf3e4`
- `generated/uem_surface/unified/__init__.py` · `generated` · `ok` · `ae6c4cd34cb4de58`
- `generated/uem_surface/unified/machine/__init__.py` · `generated` · `ok` · `d5348d3935fc71b2`
- `generated/uem_surface/unified/machine/generated_host.py` · `generated` · `ok` · `595e09c1b8294f5c`
- `generated/uem_surface/unified/machine/generated_surface.py` · `generated` · `ok` · `28b3ef421c860466`
- `generated/uem_surface/vectors/l11-surface.json` · `generated` · `ok` · `569475e5da9bc192`
- `generated/verification_surface/__init__.py` · `generated` · `ok` · `a86334931a1bdf70`
- `generated/verification_surface/audit/__init__.py` · `generated` · `ok` · `e76029b523f09f15`
- `generated/verification_surface/audit/generated_audit.py` · `generated` · `ok` · `8bbdeef4e781e648`
- `generated/verification_surface/audit/obligations.json` · `generated` · `ok` · `f5b8429a50f0ce13`
- `generated/verification_surface/audit/run_audit.py` · `generated` · `ok` · `37196aeb81802c1a`
- `generated/verification_surface/audit/schema.json` · `generated` · `ok` · `dcc5c289ca146696`
- `generated/verification_surface/authority/facts.json` · `generated` · `ok` · `e57632f0c613c593`
- `generated/verification_surface/authority/obligations.json` · `generated` · `ok` · `224f825972670ec1`
- `generated/verification_surface/c/generated_contract_test.c` · `generated` · `ok` · `c74de4e57e1dd871`
- `generated/verification_surface/coverage/contract.json` · `generated` · `ok` · `895249d0df5a226b`
- `generated/verification_surface/docs/DEVELOPER_WORKFLOW.md` · `generated` · `ok` · `859a010eb7a10b25`
- `generated/verification_surface/docs/LAW.normative.md` · `generated` · `ok` · `c6c8a3ccd5996f82`
- `generated/verification_surface/docs/README.status.md` · `generated` · `ok` · `7e00ff03dd3fd69b`
- `generated/verification_surface/docs/SPEC.normative.md` · `generated` · `ok` · `264f6429305dbe4d`
- `generated/verification_surface/docs/UEM.normative.md` · `generated` · `ok` · `d5d0004191b02819`
- `generated/verification_surface/gauntlet/contract.json` · `generated` · `ok` · `0fe90178cdae7e6d`
- `generated/verification_surface/goldens/manifest.json` · `generated` · `ok` · `02de77a73a443c38`
- `generated/verification_surface/goldens/vector-0000.json` · `generated` · `ok` · `3057fa2313fe9583`
- `generated/verification_surface/goldens/vector-0001.json` · `generated` · `ok` · `ad5f701a4e69758c`
- `generated/verification_surface/goldens/vector-0002.json` · `generated` · `ok` · `51d27795d00b9e98`
- `generated/verification_surface/goldens/vector-0003.json` · `generated` · `ok` · `c6fc307350ba9ebd`
- `generated/verification_surface/goldens/vector-0004.json` · `generated` · `ok` · `a1a2230865a07a12`
- `generated/verification_surface/goldens/vector-0005.json` · `generated` · `ok` · `460daa04c17caec9`
- `generated/verification_surface/goldens/vector-0006.json` · `generated` · `ok` · `3552ac6a95221ada`
- `generated/verification_surface/goldens/vector-0007.json` · `generated` · `ok` · `787cfe8ca6b8414c`
- `generated/verification_surface/goldens/vector-0008.json` · `generated` · `ok` · `401c15a8274905d4`
- `generated/verification_surface/goldens/vector-0009.json` · `generated` · `ok` · `18454bc901d5d578`
- `generated/verification_surface/goldens/vector-0010.json` · `generated` · `ok` · `f151b7b2a1b4b36b`
- `generated/verification_surface/goldens/vector-0011.json` · `generated` · `ok` · `d25c8dab1b9ddbae`
- `generated/verification_surface/goldens/vector-0012.json` · `generated` · `ok` · `c17b529e0a1d6706`
- `generated/verification_surface/goldens/vector-0013.json` · `generated` · `ok` · `9d7d31223557973e`
- `generated/verification_surface/goldens/vector-0014.json` · `generated` · `ok` · `1fd2b6b088102b9c`
- `generated/verification_surface/goldens/vector-0015.json` · `generated` · `ok` · `a33aae75aa090833`
- `generated/verification_surface/goldens/vector-0016.json` · `generated` · `ok` · `4e37f2377c52ba23`
- `generated/verification_surface/goldens/vector-0017.json` · `generated` · `ok` · `bd979632d1900e1c`
- `generated/verification_surface/goldens/vector-0018.json` · `generated` · `ok` · `2c7d59b536a1aed3`
- `generated/verification_surface/goldens/vector-0019.json` · `generated` · `ok` · `b9ccb1c33dca512d`
- `generated/verification_surface/goldens/vector-0020.json` · `generated` · `ok` · `3742e9ddf35eae68`
- `generated/verification_surface/goldens/vector-0021.json` · `generated` · `ok` · `3fcc244fd79f5e5c`
- `generated/verification_surface/goldens/vector-0022.json` · `generated` · `ok` · `01795901bb0f7844`
- `generated/verification_surface/goldens/vector-0023.json` · `generated` · `ok` · `7158fd2ea84de8f5`
- `generated/verification_surface/goldens/vector-0024.json` · `generated` · `ok` · `c56970ea68f921d5`
- `generated/verification_surface/goldens/vector-0025.json` · `generated` · `ok` · `d2e2902cc5ec76b2`
- `generated/verification_surface/goldens/vector-0026.json` · `generated` · `ok` · `14032d3edc187e65`
- `generated/verification_surface/goldens/vector-0027.json` · `generated` · `ok` · `4eea531145528300`
- `generated/verification_surface/goldens/vector-0028.json` · `generated` · `ok` · `0db1d39e32664b2b`
- `generated/verification_surface/goldens/vector-0029.json` · `generated` · `ok` · `fcc13abb12cf4d7b`
- `generated/verification_surface/goldens/vector-0030.json` · `generated` · `ok` · `1f8ddbba0b561857`
- `generated/verification_surface/goldens/vector-0031.json` · `generated` · `ok` · `6f02122ebc9d489d`
- `generated/verification_surface/goldens/vector-0032.json` · `generated` · `ok` · `1e8765aca3f1f897`
- `generated/verification_surface/goldens/vector-0033.json` · `generated` · `ok` · `7472a0d68fc40da2`
- `generated/verification_surface/goldens/vector-0034.json` · `generated` · `ok` · `f828ef664e19a871`
- `generated/verification_surface/goldens/vector-0035.json` · `generated` · `ok` · `1ea21b50953e17bd`
- `generated/verification_surface/goldens/vector-0036.json` · `generated` · `ok` · `3b01eee2641a6b46`
- `generated/verification_surface/goldens/vector-0037.json` · `generated` · `ok` · `ecee2d4c20b3933b`
- `generated/verification_surface/goldens/vector-0038.json` · `generated` · `ok` · `586e1a8f6ce83bc4`
- `generated/verification_surface/goldens/vector-0039.json` · `generated` · `ok` · `e33b4278a8ab6acf`
- `generated/verification_surface/goldens/vector-0040.json` · `generated` · `ok` · `3639fca157656106`
- `generated/verification_surface/goldens/vector-0041.json` · `generated` · `ok` · `e12eab651b071d74`
- `generated/verification_surface/goldens/vector-0042.json` · `generated` · `ok` · `3bb4cfa3c4433996`
- `generated/verification_surface/goldens/vector-0043.json` · `generated` · `ok` · `260affc4969cafc2`
- `generated/verification_surface/goldens/vector-0044.json` · `generated` · `ok` · `547126d217c41247`
- `generated/verification_surface/goldens/vector-0045.json` · `generated` · `ok` · `b97d2a421e5fc9a4`
- `generated/verification_surface/goldens/vector-0046.json` · `generated` · `ok` · `5a76523b8de0eac2`
- `generated/verification_surface/goldens/vector-0047.json` · `generated` · `ok` · `da0c6a4121ef4dbe`
- `generated/verification_surface/goldens/vector-0048.json` · `generated` · `ok` · `6180641858911067`
- `generated/verification_surface/goldens/vector-0049.json` · `generated` · `ok` · `e9a5885cda514a94`
- `generated/verification_surface/goldens/vector-0050.json` · `generated` · `ok` · `347e1e78709fb42e`
- `generated/verification_surface/goldens/vector-0051.json` · `generated` · `ok` · `928e3f043c6877be`
- `generated/verification_surface/goldens/vector-0052.json` · `generated` · `ok` · `7a0df56a912c0ffa`
- `generated/verification_surface/goldens/vector-0053.json` · `generated` · `ok` · `c6a05135b94bbbf8`
- `generated/verification_surface/goldens/vector-0054.json` · `generated` · `ok` · `13bab943b326eec7`
- `generated/verification_surface/goldens/vector-0055.json` · `generated` · `ok` · `57ad88cb7ebb6844`
- `generated/verification_surface/goldens/vector-0056.json` · `generated` · `ok` · `1587131bf997c7fe`
- `generated/verification_surface/goldens/vector-0057.json` · `generated` · `ok` · `fb011125c65703fa`
- `generated/verification_surface/goldens/vector-0058.json` · `generated` · `ok` · `ca157db1e93dbf7a`
- `generated/verification_surface/goldens/vector-0059.json` · `generated` · `ok` · `b31f1333bbdd2ed1`
- `generated/verification_surface/goldens/vector-0060.json` · `generated` · `ok` · `39597b14cc40748d`
- `generated/verification_surface/goldens/vector-0061.json` · `generated` · `ok` · `5d8e4eaaa7245f12`
- `generated/verification_surface/goldens/vector-0062.json` · `generated` · `ok` · `403e8259eee63e61`
- `generated/verification_surface/goldens/vector-0063.json` · `generated` · `ok` · `bb7c7a2cd6368ac4`
- `generated/verification_surface/goldens/vector-0064.json` · `generated` · `ok` · `40700eb17396bd06`
- `generated/verification_surface/goldens/vector-0065.json` · `generated` · `ok` · `d280b534e68fa1f8`
- `generated/verification_surface/goldens/vector-0066.json` · `generated` · `ok` · `89817b37f3e2c241`
- `generated/verification_surface/goldens/vector-0067.json` · `generated` · `ok` · `e8ff9137ebf1dba4`
- `generated/verification_surface/goldens/vector-0068.json` · `generated` · `ok` · `3c8d819efeae14a5`
- `generated/verification_surface/goldens/vector-0069.json` · `generated` · `ok` · `51c0c9f95d812595`
- `generated/verification_surface/goldens/vector-0070.json` · `generated` · `ok` · `6aa7fc4df602d616`
- `generated/verification_surface/goldens/vector-0071.json` · `generated` · `ok` · `ae4ab78dc98904c8`
- `generated/verification_surface/goldens/vector-0072.json` · `generated` · `ok` · `755c155177adfe56`
- `generated/verification_surface/goldens/vector-0073.json` · `generated` · `ok` · `6a51500e81fb4165`
- `generated/verification_surface/mutations/manifest.json` · `generated` · `ok` · `e05367450b3e5041`
- `generated/verification_surface/provenance.json` · `generated` · `ok` · `bac0b5bc618cb917`
- `generated/verification_surface/python/test_generated_contract.py` · `generated` · `ok` · `98c2b498887a5ad0`
- `generated/verification_surface/tests/cross-host-vectors.json` · `generated` · `ok` · `2e864d2313dd6f6b`
- `generated/verification_surface/tests/partitions.json` · `generated` · `ok` · `9ca202b862ace290`
- `generated/verification_surface/verification/ci-inventory.json` · `generated` · `ok` · `927d0f4c51c565f7`
- `generated/verification_surface/verification/proof-graph.json` · `generated` · `ok` · `53764eea58c6a6e2`
- `generated/verification_surface/verification-manifest.json` · `generated` · `ok` · `35c25b8ba50ea7aa`
- `pyproject.toml` · `handwritten-pending` · `standard.gap` · `033818aa172c883b`
- `scripts/assert_verify_budget.py` · `handwritten-pending` · `standard.gap` · `c0cff5192f23dd74`
- `scripts/audit_standard_ten.py` · `handwritten-pending` · `standard.gap` · `400c2bdc3650a4bc`
- `scripts/check_stateful_overfit.py` · `handwritten-pending` · `standard.gap` · `1068fd99ebb46984`
- `scripts/check_thing_v2_overfit.py` · `handwritten-pending` · `standard.gap` · `cdd9b75c330cb5fd`
- `scripts/clean_room_ten.sh` · `handwritten-pending` · `standard.gap` · `a25cddf4323da5c8`
- `scripts/emit_l13_report.py` · `handwritten-pending` · `standard.gap` · `3810ee0ccf9dc694`
- `scripts/run_l13.sh` · `handwritten-pending` · `standard.gap` · `f0655cb2c9a828ff`
- `scripts/run_standard_ten.sh` · `handwritten-pending` · `standard.gap` · `970611e014e21f56`
- `scripts/uc_contract` · `handwritten-pending` · `standard.gap` · `4d25b4802a3e47e7`
- `scripts/uc_contract.py` · `handwritten-pending` · `standard.gap` · `76fad072500449d6`
- `scripts/verify_l13_evidence.py` · `handwritten-pending` · `standard.gap` · `52225b679187a5e1`
- `seed/APPLICATION_SUITE_SCHEMA.json` · `seed` · `ok` · `8bc208989d14af8e`
- `seed/APPLICATION_V3_SCHEMA.json` · `seed` · `ok` · `d02d5401b7f15aa3`
- `seed/MANIFESTATION_SCHEMA.json` · `seed` · `ok` · `a7d6ea56ac0856de`
- `seed/ROOT.seed.json` · `seed` · `ok` · `9b145882d8aaa29d`
- `seed/ROOT_CONVERGENCE_SCHEMA.json` · `seed` · `ok` · `c99da7eb29b85967`
- `seed/SCHEMA.json` · `seed` · `ok` · `2682d4a51151cdb4`
- `seed/SEED_SCHEMA.md` · `seed` · `ok` · `a9ffff6174d42540`
- `seed/STAGE0_GENERATION_MANIFEST_SCHEMA.json` · `seed` · `ok` · `2edb45ebc6918a22`
- `seed/STAGE0_SCHEMA.json` · `seed` · `ok` · `3113d916ee229524`
- `seed/STAGE1_HANDOFF_SCHEMA.json` · `seed` · `ok` · `fa64bccd2d4cc1a9`
- `seed/THING_V2_SCHEMA.json` · `seed` · `ok` · `ec5fae5c8435f9c7`
- `seed/application_suite.json` · `seed` · `ok` · `592473b5a7388e7c`
- `seed/applications/calculator.json` · `seed` · `ok` · `06792940f3de50d1`
- `seed/applications/file_editor.json` · `seed` · `ok` · `5d57b5a70876780e`
- `seed/applications/file_reader.json` · `seed` · `ok` · `9819c7abd9664e3c`
- `seed/applications/math_library.json` · `seed` · `ok` · `4bd6981d8d3fae97`
- `seed/applications/pong_game.json` · `seed` · `ok` · `586a32eb164a50bb`
- `seed/declarations/invoice_total.json` · `seed` · `ok` · `fd1bb8733a2176c1`
- `seed/declarations/score_board.json` · `seed` · `ok` · `1360eaca25d0e3d2`
- `seed/declarations/task_ledger.json` · `seed` · `ok` · `cb27a8826900d431`
- `seed/declarations/text_stats_v2.json` · `seed` · `ok` · `9b0fd8aa94ded247`
- `seed/registry.json` · `seed` · `ok` · `277ad623f93d724a`
- `seed/stage0/TRUSTED_INPUTS.json` · `seed` · `ok` · `be794e079a807d00`
- `seed/stamps/generator.lock.json` · `seed` · `ok` · `f910c89e103f18a2`
- `seed/thing_v2/orchard_yield.json` · `seed` · `ok` · `dbef860d09797957`
- `seed/thing_v2/trajectory_meter.json` · `seed` · `ok` · `7d6a462785e2f846`
- `seed/verification/PROOF_BUNDLE.json` · `seed` · `ok` · `82a1770e15800c8f`
- `seed/verification/PROOF_GRAPH.json` · `seed` · `ok` · `070e52794ee21260`
- `seed/verification/SYNTHETIC_OBLIGATION.json` · `seed` · `ok` · `ae1dff1127af06ef`
- `tests/test_application_assembly.py` · `handwritten-pending` · `standard.gap` · `5c4168fc545cda85`
- `tests/test_benchmark.py` · `handwritten-pending` · `standard.gap` · `4ce9240b671a4c66`
- `tests/test_binding_mutations.py` · `handwritten-pending` · `standard.gap` · `7ad5942c665486a5`
- `tests/test_boundary.py` · `handwritten-pending` · `standard.gap` · `bfa6a879dfec4bd1`
- `tests/test_build_gauntlet.py` · `handwritten-pending` · `standard.gap` · `baa7d05da57e0fec`
- `tests/test_clock.py` · `handwritten-pending` · `standard.gap` · `39c716bc4f3bc4df`
- `tests/test_convergence.py` · `handwritten-pending` · `standard.gap` · `1743aec67b95a5e4`
- `tests/test_declaration.py` · `handwritten-pending` · `standard.gap` · `3cb0346491016cba`
- `tests/test_dimensions.py` · `handwritten-pending` · `standard.gap` · `b2b4af310463fe7e`
- `tests/test_event_l10.py` · `handwritten-pending` · `standard.gap` · `59e2df831a3e3790`
- `tests/test_expr.py` · `handwritten-pending` · `standard.gap` · `1cb5e1ff6866d5f9`
- `tests/test_generator.py` · `handwritten-pending` · `standard.gap` · `5455ca54048d663e`
- `tests/test_invariants.py` · `handwritten-pending` · `standard.gap` · `2747eda479b3b5f6`
- `tests/test_l11.py` · `handwritten-pending` · `standard.gap` · `4d863d79a39a9577`
- `tests/test_l13.py` · `handwritten-pending` · `standard.gap` · `29113370d7bca2cd`
- `tests/test_l13_coverage.py` · `handwritten-pending` · `standard.gap` · `e28ca779a05fe5c2`
- `tests/test_l13_deep.py` · `handwritten-pending` · `standard.gap` · `bf363a49551abf3e`
- `tests/test_manifestation.py` · `handwritten-pending` · `standard.gap` · `c9ef1c8bd061ddb1`
- `tests/test_no_python_declarations.py` · `handwritten-pending` · `standard.gap` · `c8552d990c2dee26`
- `tests/test_oom_mutations.py` · `handwritten-pending` · `standard.gap` · `060f8cffef0861d1`
- `tests/test_signature.py` · `handwritten-pending` · `standard.gap` · `8e640c56a6580c13`
- `tests/test_stage0.py` · `handwritten-pending` · `standard.gap` · `d02db1119138989b`
- `tests/test_stage1_bootstrap.py` · `handwritten-pending` · `standard.gap` · `b6d347ce57acefad`
- `tests/test_stage1_fixed_point.py` · `handwritten-pending` · `standard.gap` · `3d1a5fc628732923`
- `tests/test_standard_ten.py` · `handwritten-pending` · `standard.gap` · `6daf6aec6921f2df`
- `tests/test_thing_v2.py` · `handwritten-pending` · `standard.gap` · `71daee0236721782`
- `tests/test_uem.py` · `handwritten-pending` · `standard.gap` · `124d0cb0b656702c`
- `tests/test_uem_surface_generation.py` · `handwritten-pending` · `standard.gap` · `9de8badd5c9ebcd8`
- `tests/test_unfold_stateful.py` · `handwritten-pending` · `standard.gap` · `b8f3c1dcaff383cd`
- `tests/test_verification_surface_generation.py` · `handwritten-pending` · `standard.gap` · `6819675e10cd1891`
- `tests/test_verify_flow.py` · `handwritten-pending` · `standard.gap` · `4a1782da0cfa8c2f`
- `unified/__init__.py` · `handwritten-pending` · `standard.gap` · `7ffb124068950347`
- `unified/__main__.py` · `handwritten-pending` · `standard.gap` · `2b9731d81c4a0fe6`
- `unified/boundary.py` · `handwritten-pending` · `standard.gap` · `9a76b9d73f1daab0`
- `unified/clock.py` · `handwritten-pending` · `standard.gap` · `23e256961926cc5d`
- `unified/convergence.py` · `handwritten-pending` · `standard.gap` · `45408b495b5b9bf9`
- `unified/depth.py` · `handwritten-pending` · `standard.gap` · `a93f3ae1e92f0197`
- `unified/dimension.py` · `handwritten-pending` · `standard.gap` · `3aa73e22a6b6a45d`
- `unified/generator/__init__.py` · `handwritten-pending` · `standard.gap` · `802e4e2dab6e0b01`
- `unified/generator/__main__.py` · `handwritten-pending` · `standard.gap` · `3af36c6cc1597b0d`
- `unified/generator/assembly.py` · `handwritten-pending` · `standard.gap` · `3dd3a1d490a2da2d`
- `unified/generator/benchmark.py` · `handwritten-pending` · `standard.gap` · `5e3bef2b43e57115`
- `unified/generator/build.py` · `handwritten-pending` · `standard.gap` · `9af504e6250e5132`
- `unified/generator/cli.py` · `handwritten-pending` · `standard.gap` · `5d1e73fe2cf2142a`
- `unified/generator/declaration.py` · `handwritten-pending` · `standard.gap` · `eee7f3d9c10272f1`
- `unified/generator/event_emit.py` · `handwritten-pending` · `standard.gap` · `7d151b2e1fb6db0f`
- `unified/generator/expr.py` · `handwritten-pending` · `standard.gap` · `3e0971d83229403c`
- `unified/generator/expr_emit.py` · `handwritten-pending` · `standard.gap` · `d01abd88a13899e7`
- `unified/generator/gauntlet.py` · `handwritten-pending` · `standard.gap` · `5d8b79d636b348a2`
- `unified/generator/generate.py` · `handwritten-pending` · `standard.gap` · `e2f992740b0ee252`
- `unified/generator/gui.py` · `handwritten-pending` · `standard.gap` · `062ddbd6c593d13a`
- `unified/generator/manifestation.py` · `handwritten-pending` · `standard.gap` · `c80af5d52e8dbb42`
- `unified/generator/names.py` · `handwritten-pending` · `standard.gap` · `04791c2fa1ca7cf6`
- `unified/generator/overfit.py` · `handwritten-pending` · `standard.gap` · `f08f29086e672494`
- `unified/generator/render.py` · `handwritten-pending` · `standard.gap` · `c7d4a443dead9e30`
- `unified/generator/render_declared.py` · `handwritten-pending` · `standard.gap` · `b5e91bd42c4f39c8`
- `unified/generator/stateful_emit.py` · `handwritten-pending` · `standard.gap` · `5fde3760ae713587`
- `unified/generator/thing_v2.py` · `handwritten-pending` · `standard.gap` · `b79e75266ce657d0`
- `unified/generator/unfold.py` · `handwritten-pending` · `standard.gap` · `68473f68bf0418bb`
- `unified/generator/validate.py` · `handwritten-pending` · `standard.gap` · `8fb3436cc6088a28`
- `unified/generator/verify_plan.py` · `handwritten-pending` · `standard.gap` · `0e981d8721b784e0`
- `unified/generator/write_fs.py` · `handwritten-pending` · `standard.gap` · `57e811ec50762428`
- `unified/machine/__init__.py` · `handwritten-pending` · `standard.gap` · `a214cc6bcfe02875`
- `unified/machine/bytecode.py` · `handwritten-pending` · `standard.gap` · `0a7fa4266ec8f067`
- `unified/machine/canonical.py` · `handwritten-pending` · `standard.gap` · `a52356295ee86c86`
- `unified/machine/compile_decl.py` · `handwritten-pending` · `standard.gap` · `e201c3e70b87eee4`
- `unified/machine/gauntlet.py` · `handwritten-pending` · `standard.gap` · `910d737cd1cecc3f`
- `unified/machine/host.py` · `physical-host-boundary` · `ok` · `46a70046d13b66d1`
- `unified/machine/interpreter.py` · `handwritten-pending` · `standard.gap` · `123e5d0bd4804636`
- `unified/machine/l11.py` · `handwritten-pending` · `standard.gap` · `95674b18c7322017`
- `unified/machine/l13.py` · `handwritten-pending` · `standard.gap` · `85332bc9c0977640`
- `unified/machine/l13_catalog.py` · `handwritten-pending` · `standard.gap` · `e529293e40e0ad51`
- `unified/machine/measure.py` · `handwritten-pending` · `standard.gap` · `f6c3bd6f8b340780`
- `unified/machine/opcodes.py` · `handwritten-pending` · `standard.gap` · `8e04271a8acd6f0c`
- `unified/machine/primitives.py` · `handwritten-pending` · `standard.gap` · `2577c31114161b56`
- `unified/machine/stateful.py` · `handwritten-pending` · `standard.gap` · `3a856e3f0ef47ab5`
- `unified/machine/thing.py` · `handwritten-pending` · `standard.gap` · `991b7864294015f9`
- `unified/machine/validate.py` · `handwritten-pending` · `standard.gap` · `a7233a9e4015f04f`
- `unified/standard.py` · `handwritten-pending` · `standard.gap` · `8aa45f56d2948ac5`
- `unified/standard_audit.py` · `handwritten-pending` · `standard.gap` · `759c0f9a5a61280b`
- `unified/standard_generate.py` · `handwritten-pending` · `standard.gap` · `78fd6e444cffdc5d`
- `unified/thing.py` · `handwritten-pending` · `standard.gap` · `7db7669dc8e629b1`
- `unified/verify.py` · `handwritten-pending` · `standard.gap` · `d72f0665fb484a42`
- `unified/verify_flow.py` · `handwritten-pending` · `standard.gap` · `7133fc6584d67dcf`
