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
**seed_sha256:** `375956e77f77ce474f8deacba7d0aefe4ed90f2023b7819e357388a3eb03e5e3`
**files classified:** 249
**illegal provenance (not in allowed five classes):** 205
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
| `generated` | 8 |
| `handwritten-pending` | 205 |
| `physical-host-boundary` | 16 |
| `seed` | 9 |

## Clean-room status

Full-tree clean-room regeneration is **not** claimed. See `gap.clean-room-full-tree`. Partial regeneration of seed-locked UEM artifacts is exercised by `scripts/clean_room_ten.sh`.

## File table (path · class · compliance · sha256[:16])

- `.coverage` · `evidence` · `ok` · `0582dadf4a76f6ed`
- `.coveragerc` · `handwritten-pending` · `standard.gap` · `f4c1eac25e83d766`
- `.github/workflows/test.yml` · `handwritten-pending` · `standard.gap` · `daf9dc9485d797c6`
- `.gitignore` · `handwritten-pending` · `standard.gap` · `699c693cc407b221`
- `AUDIT_STANDARD_TEN.md` · `evidence` · `ok` · `77f09a4f06fb4049`
- `GAUNTLET.md` · `evidence` · `ok` · `82dd4e6dd71de69e`
- `LAW.md` · `handwritten-pending` · `standard.gap` · `7d452c174dec7c94`
- `LICENSE` · `handwritten-pending` · `standard.gap` · `af6b910929ec375c`
- `PROVENANCE_MANIFEST.json` · `evidence` · `ok` · `1625306dc8b100f1`
- `README.md` · `handwritten-pending` · `standard.gap` · `3aa93174bd037940`
- `ROADMAP.md` · `handwritten-pending` · `standard.gap` · `b34e2c9c65b54d35`
- `SPEC.md` · `handwritten-pending` · `standard.gap` · `fb04ba1772610eb3`
- `STANDARD_TEN.md` · `seed` · `ok` · `28bcb6c07dc035ce`
- `UEM_SPEC.md` · `handwritten-pending` · `standard.gap` · `6bfacbc86a486beb`
- `artifacts/uem/invoice_total/program.symbolic.json` · `generated` · `ok` · `a1899fe0c2f6ac40`
- `artifacts/uem/invoice_total/program.symbolic.json.stamp.json` · `generated` · `ok` · `d44578b02edc54de`
- `artifacts/uem/invoice_total/program.uem` · `generated` · `ok` · `cf2a87a8219f26e5`
- `artifacts/uem/invoice_total/program.uem.stamp.json` · `generated` · `ok` · `b6e0134ac7043ea5`
- `artifacts/uem/text_stats_v2/program.symbolic.json` · `generated` · `ok` · `2813f009eccd6cd9`
- `artifacts/uem/text_stats_v2/program.symbolic.json.stamp.json` · `generated` · `ok` · `6c0850565dc2628e`
- `artifacts/uem/text_stats_v2/program.uem` · `generated` · `ok` · `b625f4a2104df5a4`
- `artifacts/uem/text_stats_v2/program.uem.stamp.json` · `generated` · `ok` · `a756042213f3087c`
- `c/.gitignore` · `handwritten-pending` · `standard.gap` · `2dc3b312a4902f53`
- `c/Makefile` · `handwritten-pending` · `standard.gap` · `f40326d9bf9dd16c`
- `c/README.md` · `handwritten-pending` · `standard.gap` · `84a0d2f879ecac82`
- `c/REGISTRY.md` · `handwritten-pending` · `standard.gap` · `1a496cfe8a053065`
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
- `c/include/uem.h` · `physical-host-boundary` · `ok` · `87720fdc5935ec49`
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
- `c/targets/manifests/l12_report_x86_64.json` · `evidence` · `ok` · `103a46f650e14a4b`
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
- `coverage.json` · `evidence` · `ok` · `d1ee69712e13e6b9`
- `coverage_py.json` · `evidence` · `ok` · `3c7d91adbf12debd`
- `docs/DEVELOPER_WORKFLOW.md` · `handwritten-pending` · `standard.gap` · `5ce70a955dc69a2c`
- `examples/declarations/invoice_total.json` · `handwritten-pending` · `standard.gap` · `1a0479e011592752`
- `examples/declarations/invoice_total.py` · `handwritten-pending` · `standard.gap` · `d0cb833aace2a12a`
- `examples/declarations/text_stats_program.json` · `handwritten-pending` · `standard.gap` · `c8c1c8f23b4e780a`
- `examples/declarations/text_stats_program.py` · `handwritten-pending` · `standard.gap` · `d9d565c596a5efdd`
- `examples/declarations/text_stats_v2.json` · `handwritten-pending` · `standard.gap` · `ac4a679c4e32180f`
- `examples/declarations/text_stats_v2.py` · `handwritten-pending` · `standard.gap` · `0c083c7704d22e8d`
- `examples/one_dimension.py` · `handwritten-pending` · `standard.gap` · `48d90d21a1e77ced`
- `examples/three_dimensions.py` · `handwritten-pending` · `standard.gap` · `a5bc88a92e9fcf54`
- `examples/two_dimensions.py` · `handwritten-pending` · `standard.gap` · `a6eec3842bbbe930`
- `pyproject.toml` · `handwritten-pending` · `standard.gap` · `033818aa172c883b`
- `scripts/audit_standard_ten.py` · `handwritten-pending` · `standard.gap` · `400c2bdc3650a4bc`
- `scripts/check_stateful_overfit.py` · `handwritten-pending` · `standard.gap` · `1068fd99ebb46984`
- `scripts/clean_room_ten.sh` · `handwritten-pending` · `standard.gap` · `a25cddf4323da5c8`
- `scripts/emit_l13_report.py` · `handwritten-pending` · `standard.gap` · `3810ee0ccf9dc694`
- `scripts/run_l13.sh` · `handwritten-pending` · `standard.gap` · `f0655cb2c9a828ff`
- `scripts/run_standard_ten.sh` · `handwritten-pending` · `standard.gap` · `970611e014e21f56`
- `scripts/uc_contract` · `handwritten-pending` · `standard.gap` · `4d25b4802a3e47e7`
- `scripts/uc_contract.py` · `handwritten-pending` · `standard.gap` · `76fad072500449d6`
- `seed/ROOT.seed.json` · `seed` · `ok` · `375956e77f77ce47`
- `seed/SCHEMA.json` · `seed` · `ok` · `61776cb0433eff8b`
- `seed/SEED_SCHEMA.md` · `seed` · `ok` · `a9ffff6174d42540`
- `seed/declarations/invoice_total.json` · `seed` · `ok` · `fd1bb8733a2176c1`
- `seed/declarations/score_board.json` · `seed` · `ok` · `1360eaca25d0e3d2`
- `seed/declarations/task_ledger.json` · `seed` · `ok` · `cb27a8826900d431`
- `seed/declarations/text_stats_v2.json` · `seed` · `ok` · `9b0fd8aa94ded247`
- `seed/stamps/generator.lock.json` · `seed` · `ok` · `eab941fad387f2b9`
- `tests/test_benchmark.py` · `handwritten-pending` · `standard.gap` · `4ce9240b671a4c66`
- `tests/test_binding_mutations.py` · `handwritten-pending` · `standard.gap` · `7ad5942c665486a5`
- `tests/test_boundary.py` · `handwritten-pending` · `standard.gap` · `bfa6a879dfec4bd1`
- `tests/test_build_gauntlet.py` · `handwritten-pending` · `standard.gap` · `baa7d05da57e0fec`
- `tests/test_clock.py` · `handwritten-pending` · `standard.gap` · `39c716bc4f3bc4df`
- `tests/test_declaration.py` · `handwritten-pending` · `standard.gap` · `3cb0346491016cba`
- `tests/test_dimensions.py` · `handwritten-pending` · `standard.gap` · `b2b4af310463fe7e`
- `tests/test_event_l10.py` · `handwritten-pending` · `standard.gap` · `59e2df831a3e3790`
- `tests/test_expr.py` · `handwritten-pending` · `standard.gap` · `1cb5e1ff6866d5f9`
- `tests/test_generator.py` · `handwritten-pending` · `standard.gap` · `5455ca54048d663e`
- `tests/test_invariants.py` · `handwritten-pending` · `standard.gap` · `2747eda479b3b5f6`
- `tests/test_l11.py` · `handwritten-pending` · `standard.gap` · `b4500532c720112d`
- `tests/test_l13.py` · `handwritten-pending` · `standard.gap` · `29113370d7bca2cd`
- `tests/test_l13_coverage.py` · `handwritten-pending` · `standard.gap` · `e28ca779a05fe5c2`
- `tests/test_l13_deep.py` · `handwritten-pending` · `standard.gap` · `bf363a49551abf3e`
- `tests/test_no_python_declarations.py` · `handwritten-pending` · `standard.gap` · `c8552d990c2dee26`
- `tests/test_oom_mutations.py` · `handwritten-pending` · `standard.gap` · `060f8cffef0861d1`
- `tests/test_signature.py` · `handwritten-pending` · `standard.gap` · `8e640c56a6580c13`
- `tests/test_standard_ten.py` · `handwritten-pending` · `standard.gap` · `6daf6aec6921f2df`
- `tests/test_uem.py` · `handwritten-pending` · `standard.gap` · `124d0cb0b656702c`
- `tests/test_unfold_stateful.py` · `handwritten-pending` · `standard.gap` · `ceb9cd3ac3e9d050`
- `unified/__init__.py` · `handwritten-pending` · `standard.gap` · `24a5176c9cd5a7f9`
- `unified/__main__.py` · `handwritten-pending` · `standard.gap` · `2b9731d81c4a0fe6`
- `unified/boundary.py` · `handwritten-pending` · `standard.gap` · `9a76b9d73f1daab0`
- `unified/clock.py` · `handwritten-pending` · `standard.gap` · `23e256961926cc5d`
- `unified/depth.py` · `handwritten-pending` · `standard.gap` · `a93f3ae1e92f0197`
- `unified/dimension.py` · `handwritten-pending` · `standard.gap` · `3aa73e22a6b6a45d`
- `unified/generator/__init__.py` · `handwritten-pending` · `standard.gap` · `da249896c044c98c`
- `unified/generator/__main__.py` · `handwritten-pending` · `standard.gap` · `3af36c6cc1597b0d`
- `unified/generator/benchmark.py` · `handwritten-pending` · `standard.gap` · `5e3bef2b43e57115`
- `unified/generator/build.py` · `handwritten-pending` · `standard.gap` · `9af504e6250e5132`
- `unified/generator/cli.py` · `handwritten-pending` · `standard.gap` · `94385e4e1e188b74`
- `unified/generator/declaration.py` · `handwritten-pending` · `standard.gap` · `eee7f3d9c10272f1`
- `unified/generator/event_emit.py` · `handwritten-pending` · `standard.gap` · `7d151b2e1fb6db0f`
- `unified/generator/expr.py` · `handwritten-pending` · `standard.gap` · `3e0971d83229403c`
- `unified/generator/expr_emit.py` · `handwritten-pending` · `standard.gap` · `d01abd88a13899e7`
- `unified/generator/gauntlet.py` · `handwritten-pending` · `standard.gap` · `5d8b79d636b348a2`
- `unified/generator/generate.py` · `handwritten-pending` · `standard.gap` · `e2f992740b0ee252`
- `unified/generator/names.py` · `handwritten-pending` · `standard.gap` · `04791c2fa1ca7cf6`
- `unified/generator/overfit.py` · `handwritten-pending` · `standard.gap` · `c1fccbcfd277faa1`
- `unified/generator/render.py` · `handwritten-pending` · `standard.gap` · `c7d4a443dead9e30`
- `unified/generator/render_declared.py` · `handwritten-pending` · `standard.gap` · `b5e91bd42c4f39c8`
- `unified/generator/stateful_emit.py` · `handwritten-pending` · `standard.gap` · `5fde3760ae713587`
- `unified/generator/unfold.py` · `handwritten-pending` · `standard.gap` · `2811f7f2161a0199`
- `unified/generator/validate.py` · `handwritten-pending` · `standard.gap` · `8fb3436cc6088a28`
- `unified/generator/verify_plan.py` · `handwritten-pending` · `standard.gap` · `0e981d8721b784e0`
- `unified/generator/write_fs.py` · `handwritten-pending` · `standard.gap` · `57e811ec50762428`
- `unified/machine/__init__.py` · `handwritten-pending` · `standard.gap` · `a214cc6bcfe02875`
- `unified/machine/bytecode.py` · `handwritten-pending` · `standard.gap` · `0a7fa4266ec8f067`
- `unified/machine/canonical.py` · `handwritten-pending` · `standard.gap` · `0221102fe36bd7d5`
- `unified/machine/compile_decl.py` · `handwritten-pending` · `standard.gap` · `e201c3e70b87eee4`
- `unified/machine/gauntlet.py` · `handwritten-pending` · `standard.gap` · `910d737cd1cecc3f`
- `unified/machine/host.py` · `physical-host-boundary` · `ok` · `46a70046d13b66d1`
- `unified/machine/interpreter.py` · `handwritten-pending` · `standard.gap` · `123e5d0bd4804636`
- `unified/machine/l11.py` · `handwritten-pending` · `standard.gap` · `511327326cbe6cdc`
- `unified/machine/l13.py` · `handwritten-pending` · `standard.gap` · `85332bc9c0977640`
- `unified/machine/l13_catalog.py` · `handwritten-pending` · `standard.gap` · `e529293e40e0ad51`
- `unified/machine/measure.py` · `handwritten-pending` · `standard.gap` · `f6c3bd6f8b340780`
- `unified/machine/opcodes.py` · `handwritten-pending` · `standard.gap` · `97cc810a83ccc046`
- `unified/machine/primitives.py` · `handwritten-pending` · `standard.gap` · `2577c31114161b56`
- `unified/machine/stateful.py` · `handwritten-pending` · `standard.gap` · `3a856e3f0ef47ab5`
- `unified/machine/thing.py` · `handwritten-pending` · `standard.gap` · `991b7864294015f9`
- `unified/machine/validate.py` · `handwritten-pending` · `standard.gap` · `a7233a9e4015f04f`
- `unified/standard.py` · `handwritten-pending` · `standard.gap` · `8aa45f56d2948ac5`
- `unified/standard_audit.py` · `handwritten-pending` · `standard.gap` · `67738b2208dcd8da`
- `unified/standard_generate.py` · `handwritten-pending` · `standard.gap` · `78fd6e444cffdc5d`
- `unified/thing.py` · `handwritten-pending` · `standard.gap` · `7db7669dc8e629b1`
- `unified/verify.py` · `handwritten-pending` · `standard.gap` · `d72f0665fb484a42`
