# Standard Ten Repository Audit

**Verdict:** `fail`
**standard_version:** TEN-1
**seed_sha256:** `bcd58991e3a7b754a7369a0ac44dcb3b9e3c3673013e4dfcf5293d68097307cf`
**files classified:** 305
**illegal provenance (not in allowed five classes):** 266
**OOP class files:** 1
**open standard.gap tickets:** 7

## Non-fallback law

Conventional development is not an authorized fallback. Gaps below are `standard.gap` — not invitations to implement with OOP, handwritten app logic, or dual interface stacks.

## Open gaps

- **gap.seed-expresses-full-framework** (rule 3): UEM machine, generator, and framework modules are not yet fully expressed as seed package bodies; currently handwritten under unified/.
- **gap.no-app-control-flow-in-host** (rule 6): Python/C UEM hosts still use imperative control flow (required for physical boundary execution until seed can emit hosts).
- **gap.oop-exprfail** (rule 5): unified/machine/primitives.py defines class _ExprFail — forbidden OOP; must become plain-data fault path.
- **gap.declarations-as-python** (rule 4): Application declarations live as .py modules with Python syntax; must be pure JSON under seed/declarations/.
- **gap.dual-host-not-single-machine-surface** (rule 7): Python and C interpreters are parallel implementations; Standard Ten requires one UEM with hosts as boundaries only. Semantic parity is proven (L11) but structure is dual-impl.
- **gap.generated-tests-and-docs** (rule 10): Tests and documentation are handwritten, not generated from seed/declaration.
- **gap.clean-room-full-tree** (rule 3): Clean-room regeneration cannot yet emit the full repository from seed alone.

## OOP violations

- `unified/machine/primitives.py`

## Provenance summary

| Class | Count |
| --- | ---: |
| `evidence` | 7 |
| `external-vendored` | 4 |
| `generated` | 8 |
| `handwritten-pending` | 266 |
| `physical-host-boundary` | 13 |
| `seed` | 7 |

## Clean-room status

Full-tree clean-room regeneration is **not** claimed. See `gap.clean-room-full-tree`. Partial regeneration of seed-locked UEM artifacts is exercised by `scripts/clean_room_ten.sh`.

## File table (path · class · compliance · sha256[:16])

- `.coverage` · `evidence` · `ok` · `b30fd7699c94595f`
- `.coveragerc` · `handwritten-pending` · `standard.gap` · `f4c1eac25e83d766`
- `.github/workflows/test.yml` · `handwritten-pending` · `standard.gap` · `57cf4c45308821b0`
- `.gitignore` · `handwritten-pending` · `standard.gap` · `3a86022b6133cba2`
- `AUDIT_STANDARD_TEN.md` · `evidence` · `ok` · `addea878f87896e9`
- `GAUNTLET.md` · `evidence` · `ok` · `1376f7803b8932a1`
- `LAW.md` · `handwritten-pending` · `standard.gap` · `7d452c174dec7c94`
- `LICENSE` · `handwritten-pending` · `standard.gap` · `af6b910929ec375c`
- `PROVENANCE_MANIFEST.json` · `evidence` · `ok` · `7a83ae0ddf58df90`
- `README.md` · `handwritten-pending` · `standard.gap` · `bb1782f48e375960`
- `ROADMAP.md` · `handwritten-pending` · `standard.gap` · `51123dc7e6a4fcc7`
- `SPEC.md` · `handwritten-pending` · `standard.gap` · `fb04ba1772610eb3`
- `STANDARD_TEN.md` · `seed` · `ok` · `28bcb6c07dc035ce`
- `UEM_SPEC.md` · `handwritten-pending` · `standard.gap` · `936fd94aafda7049`
- `artifacts/uem/invoice_total/program.symbolic.json` · `generated` · `ok` · `af0807511ee2dedb`
- `artifacts/uem/invoice_total/program.symbolic.json.stamp.json` · `generated` · `ok` · `616a42427c0a48ab`
- `artifacts/uem/invoice_total/program.uem` · `generated` · `ok` · `a79c68a10f78ccde`
- `artifacts/uem/invoice_total/program.uem.stamp.json` · `generated` · `ok` · `efba50dda4407fef`
- `artifacts/uem/text_stats_v2/program.symbolic.json` · `generated` · `ok` · `2813f009eccd6cd9`
- `artifacts/uem/text_stats_v2/program.symbolic.json.stamp.json` · `generated` · `ok` · `5242eb35a889b508`
- `artifacts/uem/text_stats_v2/program.uem` · `generated` · `ok` · `b625f4a2104df5a4`
- `artifacts/uem/text_stats_v2/program.uem.stamp.json` · `generated` · `ok` · `f10e1f07a72628a3`
- `c/.gitignore` · `handwritten-pending` · `standard.gap` · `2dc3b312a4902f53`
- `c/Makefile` · `handwritten-pending` · `standard.gap` · `998b9b52742be447`
- `c/README.md` · `handwritten-pending` · `standard.gap` · `84a0d2f879ecac82`
- `c/REGISTRY.md` · `handwritten-pending` · `standard.gap` · `d7c442594208b63b`
- `c/core/decimal.c` · `physical-host-boundary` · `ok` · `93841b42d3cc37f6`
- `c/core/decimal.h` · `physical-host-boundary` · `ok` · `a9ca485106343638`
- `c/core/decode.c` · `physical-host-boundary` · `ok` · `7962b1f6ebc88a75`
- `c/core/expr.c` · `physical-host-boundary` · `ok` · `9ece3fac8d98af83`
- `c/core/machine.c` · `physical-host-boundary` · `ok` · `3a5c1ac10157b419`
- `c/core/machine_internal.h` · `physical-host-boundary` · `ok` · `292aa154c1de6877`
- `c/core/primitives.c` · `physical-host-boundary` · `ok` · `2a3933f7bf220038`
- `c/host/mcu/mcu_host.c` · `physical-host-boundary` · `ok` · `8d18055f3f71ec77`
- `c/host/mcu/uem_mcu.h` · `physical-host-boundary` · `ok` · `ba4469916eabbd40`
- `c/host/posix/main.c` · `physical-host-boundary` · `ok` · `914baadeac10ade2`
- `c/host/wasm/main.c` · `physical-host-boundary` · `ok` · `4a9da23c975b1e02`
- `c/include/uem.h` · `physical-host-boundary` · `ok` · `7e545ca02bea2564`
- `c/scripts/build_cross.sh` · `handwritten-pending` · `standard.gap` · `177d91a9e6f2587a`
- `c/scripts/diff_py_c.sh` · `handwritten-pending` · `standard.gap` · `0e2dd679c4f3907e`
- `c/scripts/fuzz_bytecode.py` · `handwritten-pending` · `standard.gap` · `c6588410a65b5a72`
- `c/scripts/fuzz_l12.py` · `handwritten-pending` · `standard.gap` · `7e8f4a6f27d52a72`
- `c/scripts/gen_golden.sh` · `handwritten-pending` · `standard.gap` · `8abb12c698b97e88`
- `c/scripts/run_l11_full.sh` · `handwritten-pending` · `standard.gap` · `7d2cc34998478d50`
- `c/scripts/run_l12_report.py` · `handwritten-pending` · `standard.gap` · `3f164bed4aa8763a`
- `c/scripts/run_tests.sh` · `handwritten-pending` · `standard.gap` · `aaf230b1f4c73ece`
- `c/targets/manifests/l12_report_x86_64.json` · `evidence` · `ok` · `35e1236f99f0041b`
- `c/tests/fuzz_corpus/seed_0000.uem` · `handwritten-pending` · `standard.gap` · `b625f4a2104df5a4`
- `c/tests/fuzz_corpus/seed_0001.uem` · `handwritten-pending` · `standard.gap` · `b625f4a2104df5a4`
- `c/tests/fuzz_corpus/seed_0002.uem` · `handwritten-pending` · `standard.gap` · `cf2a87a8219f26e5`
- `c/tests/fuzz_corpus/seed_0003.uem` · `handwritten-pending` · `standard.gap` · `b6c3b364445086f5`
- `c/tests/fuzz_corpus/seed_0004.uem` · `handwritten-pending` · `standard.gap` · `9beeba5b4c4b4d6d`
- `c/tests/fuzz_corpus/seed_0005.uem` · `handwritten-pending` · `standard.gap` · `0bc7649914086bc7`
- `c/tests/fuzz_corpus/seed_0006.uem` · `handwritten-pending` · `standard.gap` · `2ea6e97a6a0c876f`
- `c/tests/fuzz_corpus/seed_0007.uem` · `handwritten-pending` · `standard.gap` · `af886cc0f7d670b2`
- `c/tests/fuzz_corpus/seed_0008.uem` · `handwritten-pending` · `standard.gap` · `2ea6e97a6a0c876f`
- `c/tests/fuzz_corpus/seed_0009.uem` · `handwritten-pending` · `standard.gap` · `62b0807e71ac7988`
- `c/tests/fuzz_corpus/seed_0010.uem` · `handwritten-pending` · `standard.gap` · `a74cba9abb9d6809`
- `c/tests/fuzz_corpus/seed_0011.uem` · `handwritten-pending` · `standard.gap` · `cf15c41706455dcb`
- `c/tests/fuzz_corpus/seed_0012.uem` · `handwritten-pending` · `standard.gap` · `4c2d094543d01aac`
- `c/tests/fuzz_corpus/seed_0013.uem` · `handwritten-pending` · `standard.gap` · `62b0807e71ac7988`
- `c/tests/fuzz_corpus/seed_0014.uem` · `handwritten-pending` · `standard.gap` · `e1809420d55cd1e0`
- `c/tests/fuzz_corpus/seed_0015.uem` · `handwritten-pending` · `standard.gap` · `ab661832955529d3`
- `c/tests/fuzz_corpus/seed_0016.uem` · `handwritten-pending` · `standard.gap` · `12924b0e0e9ba87c`
- `c/tests/fuzz_corpus/seed_0017.uem` · `handwritten-pending` · `standard.gap` · `7867b0814b0196e2`
- `c/tests/fuzz_corpus/seed_0018.uem` · `handwritten-pending` · `standard.gap` · `95647a5850ac82dd`
- `c/tests/fuzz_corpus/seed_0019.uem` · `handwritten-pending` · `standard.gap` · `2ea6e97a6a0c876f`
- `c/tests/fuzz_corpus/seed_0020.uem` · `handwritten-pending` · `standard.gap` · `acfeffdbfd992f77`
- `c/tests/fuzz_corpus/seed_0021.uem` · `handwritten-pending` · `standard.gap` · `2ea6e97a6a0c876f`
- `c/tests/fuzz_corpus/seed_0022.uem` · `handwritten-pending` · `standard.gap` · `b41edab3ba1c6702`
- `c/tests/fuzz_corpus/seed_0023.uem` · `handwritten-pending` · `standard.gap` · `2ea6e97a6a0c876f`
- `c/tests/fuzz_corpus/seed_0024.uem` · `handwritten-pending` · `standard.gap` · `cb074a97327611ff`
- `c/tests/fuzz_corpus/seed_0025.uem` · `handwritten-pending` · `standard.gap` · `963777201d797a0a`
- `c/tests/fuzz_corpus/seed_0026.uem` · `handwritten-pending` · `standard.gap` · `cf622470c391b290`
- `c/tests/fuzz_corpus/seed_0027.uem` · `handwritten-pending` · `standard.gap` · `ff3b2c2111c0909f`
- `c/tests/fuzz_corpus/seed_0028.uem` · `handwritten-pending` · `standard.gap` · `274fbb1a8daa1793`
- `c/tests/fuzz_corpus/seed_0029.uem` · `handwritten-pending` · `standard.gap` · `56187646f723f633`
- `c/tests/fuzz_corpus/seed_0030.uem` · `handwritten-pending` · `standard.gap` · `88f1f540f45ef54c`
- `c/tests/fuzz_corpus/seed_0031.uem` · `handwritten-pending` · `standard.gap` · `3dbfbf5bfa65fbf6`
- `c/tests/fuzz_corpus/seed_0032.uem` · `handwritten-pending` · `standard.gap` · `4e3ebc4e323b676b`
- `c/tests/fuzz_corpus/seed_0033.uem` · `handwritten-pending` · `standard.gap` · `71efa077f37c5a65`
- `c/tests/fuzz_corpus/seed_0034.uem` · `handwritten-pending` · `standard.gap` · `2ea6e97a6a0c876f`
- `c/tests/golden/inv_basic.json` · `handwritten-pending` · `standard.gap` · `1cffc056093fad31`
- `c/tests/golden/inv_empty_items.json` · `handwritten-pending` · `standard.gap` · `701f8bf595c77e5f`
- `c/tests/golden/ts_empty.json` · `handwritten-pending` · `standard.gap` · `fb2833ada7254b1f`
- `c/tests/golden/ts_gogo.json` · `handwritten-pending` · `standard.gap` · `1a5902131e957286`
- `c/tests/regressions/fuzz_016b127bfaa2e52e.txt` · `handwritten-pending` · `standard.gap` · `cc19132f4821f755`
- `c/tests/regressions/fuzz_016b127bfaa2e52e.uem` · `handwritten-pending` · `standard.gap` · `016b127bfaa2e52e`
- `c/tests/regressions/fuzz_02df0902124a67d0.txt` · `handwritten-pending` · `standard.gap` · `07cd44e391337465`
- `c/tests/regressions/fuzz_02df0902124a67d0.uem` · `handwritten-pending` · `standard.gap` · `02df0902124a67d0`
- `c/tests/regressions/fuzz_030f2a3efe041b6e.txt` · `handwritten-pending` · `standard.gap` · `aeb30faf3196f3bd`
- `c/tests/regressions/fuzz_030f2a3efe041b6e.uem` · `handwritten-pending` · `standard.gap` · `030f2a3efe041b6e`
- `c/tests/regressions/fuzz_046dd3780ffeced1.txt` · `handwritten-pending` · `standard.gap` · `71ad1647766dbfdc`
- `c/tests/regressions/fuzz_046dd3780ffeced1.uem` · `handwritten-pending` · `standard.gap` · `046dd3780ffeced1`
- `c/tests/regressions/fuzz_085e87c4d9643d60.txt` · `handwritten-pending` · `standard.gap` · `73d1bbe271176d6a`
- `c/tests/regressions/fuzz_085e87c4d9643d60.uem` · `handwritten-pending` · `standard.gap` · `085e87c4d9643d60`
- `c/tests/regressions/fuzz_130c468449982615.txt` · `handwritten-pending` · `standard.gap` · `4865ed246209c564`
- `c/tests/regressions/fuzz_130c468449982615.uem` · `handwritten-pending` · `standard.gap` · `130c468449982615`
- `c/tests/regressions/fuzz_165f425006539c1e.txt` · `handwritten-pending` · `standard.gap` · `4162f85f277e98a6`
- `c/tests/regressions/fuzz_165f425006539c1e.uem` · `handwritten-pending` · `standard.gap` · `165f425006539c1e`
- `c/tests/regressions/fuzz_1a7af3734835d876.txt` · `handwritten-pending` · `standard.gap` · `ea5aa75e699a5295`
- `c/tests/regressions/fuzz_1a7af3734835d876.uem` · `handwritten-pending` · `standard.gap` · `1a7af3734835d876`
- `c/tests/regressions/fuzz_1d2c0a398ad5a34a.txt` · `handwritten-pending` · `standard.gap` · `ff2cee9857efedca`
- `c/tests/regressions/fuzz_1d2c0a398ad5a34a.uem` · `handwritten-pending` · `standard.gap` · `1d2c0a398ad5a34a`
- `c/tests/regressions/fuzz_2d6687775ba0eae2.txt` · `handwritten-pending` · `standard.gap` · `a73836274c85c498`
- `c/tests/regressions/fuzz_2d6687775ba0eae2.uem` · `handwritten-pending` · `standard.gap` · `2d6687775ba0eae2`
- `c/tests/regressions/fuzz_34a055b36f027a56.txt` · `handwritten-pending` · `standard.gap` · `71f9910c756caba1`
- `c/tests/regressions/fuzz_34a055b36f027a56.uem` · `handwritten-pending` · `standard.gap` · `34a055b36f027a56`
- `c/tests/regressions/fuzz_3bb8b1568233ba49.txt` · `handwritten-pending` · `standard.gap` · `f53fff76d50c2997`
- `c/tests/regressions/fuzz_3bb8b1568233ba49.uem` · `handwritten-pending` · `standard.gap` · `3bb8b1568233ba49`
- `c/tests/regressions/fuzz_3ddeb32e6328efce.txt` · `handwritten-pending` · `standard.gap` · `1ada822043f0e38f`
- `c/tests/regressions/fuzz_3ddeb32e6328efce.uem` · `handwritten-pending` · `standard.gap` · `3ddeb32e6328efce`
- `c/tests/regressions/fuzz_3fb57f87f5cb937f.txt` · `handwritten-pending` · `standard.gap` · `9481fa6841f7d3b9`
- `c/tests/regressions/fuzz_3fb57f87f5cb937f.uem` · `handwritten-pending` · `standard.gap` · `3fb57f87f5cb937f`
- `c/tests/regressions/fuzz_44e53f1b3493c125.txt` · `handwritten-pending` · `standard.gap` · `756db68c6e3e3f3a`
- `c/tests/regressions/fuzz_44e53f1b3493c125.uem` · `handwritten-pending` · `standard.gap` · `44e53f1b3493c125`
- `c/tests/regressions/fuzz_46d878410e09549e.txt` · `handwritten-pending` · `standard.gap` · `4afe067ee9ee4c65`
- `c/tests/regressions/fuzz_46d878410e09549e.uem` · `handwritten-pending` · `standard.gap` · `46d878410e09549e`
- `c/tests/regressions/fuzz_4ccb4614f9e51dca.txt` · `handwritten-pending` · `standard.gap` · `fda521941550af3d`
- `c/tests/regressions/fuzz_4ccb4614f9e51dca.uem` · `handwritten-pending` · `standard.gap` · `4ccb4614f9e51dca`
- `c/tests/regressions/fuzz_4da6bb17e5229f56.txt` · `handwritten-pending` · `standard.gap` · `cf00a009a81af21b`
- `c/tests/regressions/fuzz_4da6bb17e5229f56.uem` · `handwritten-pending` · `standard.gap` · `4da6bb17e5229f56`
- `c/tests/regressions/fuzz_5165c0391495e268.txt` · `handwritten-pending` · `standard.gap` · `eacd2bd7a50efc24`
- `c/tests/regressions/fuzz_5165c0391495e268.uem` · `handwritten-pending` · `standard.gap` · `5165c0391495e268`
- `c/tests/regressions/fuzz_5385e5049cccdebe.txt` · `handwritten-pending` · `standard.gap` · `2c61bf67e767ba14`
- `c/tests/regressions/fuzz_5385e5049cccdebe.uem` · `handwritten-pending` · `standard.gap` · `5385e5049cccdebe`
- `c/tests/regressions/fuzz_545cf635af05befb.txt` · `handwritten-pending` · `standard.gap` · `b27447febeceeaec`
- `c/tests/regressions/fuzz_545cf635af05befb.uem` · `handwritten-pending` · `standard.gap` · `545cf635af05befb`
- `c/tests/regressions/fuzz_55c59997f7a2d4af.txt` · `handwritten-pending` · `standard.gap` · `25829f786d5137b4`
- `c/tests/regressions/fuzz_55c59997f7a2d4af.uem` · `handwritten-pending` · `standard.gap` · `55c59997f7a2d4af`
- `c/tests/regressions/fuzz_5d44e00ffe7a0fa2.txt` · `handwritten-pending` · `standard.gap` · `9ac1f500ed3c5587`
- `c/tests/regressions/fuzz_5d44e00ffe7a0fa2.uem` · `handwritten-pending` · `standard.gap` · `5d44e00ffe7a0fa2`
- `c/tests/regressions/fuzz_62b0807e71ac7988.txt` · `handwritten-pending` · `standard.gap` · `17334504765ff03a`
- `c/tests/regressions/fuzz_62b0807e71ac7988.uem` · `handwritten-pending` · `standard.gap` · `62b0807e71ac7988`
- `c/tests/regressions/fuzz_6cdab13c65ff94ec.txt` · `handwritten-pending` · `standard.gap` · `a0e75266d519478d`
- `c/tests/regressions/fuzz_6cdab13c65ff94ec.uem` · `handwritten-pending` · `standard.gap` · `6cdab13c65ff94ec`
- `c/tests/regressions/fuzz_6d1021c93c9162f4.txt` · `handwritten-pending` · `standard.gap` · `1ae128d6b84b7467`
- `c/tests/regressions/fuzz_6d1021c93c9162f4.uem` · `handwritten-pending` · `standard.gap` · `6d1021c93c9162f4`
- `c/tests/regressions/fuzz_71aa3001ba619b73.txt` · `handwritten-pending` · `standard.gap` · `e451e538a29b304f`
- `c/tests/regressions/fuzz_71aa3001ba619b73.uem` · `handwritten-pending` · `standard.gap` · `71aa3001ba619b73`
- `c/tests/regressions/fuzz_8125fef29b05db21.txt` · `handwritten-pending` · `standard.gap` · `e260de86d4e829be`
- `c/tests/regressions/fuzz_8125fef29b05db21.uem` · `handwritten-pending` · `standard.gap` · `8125fef29b05db21`
- `c/tests/regressions/fuzz_81646a7945033a59.txt` · `handwritten-pending` · `standard.gap` · `f555a120bcb843f6`
- `c/tests/regressions/fuzz_81646a7945033a59.uem` · `handwritten-pending` · `standard.gap` · `81646a7945033a59`
- `c/tests/regressions/fuzz_820237fffa6219f5.txt` · `handwritten-pending` · `standard.gap` · `64f71453c0c27111`
- `c/tests/regressions/fuzz_820237fffa6219f5.uem` · `handwritten-pending` · `standard.gap` · `820237fffa6219f5`
- `c/tests/regressions/fuzz_886e2ebe90004155.txt` · `handwritten-pending` · `standard.gap` · `b3c486cd2e5d1c49`
- `c/tests/regressions/fuzz_886e2ebe90004155.uem` · `handwritten-pending` · `standard.gap` · `886e2ebe90004155`
- `c/tests/regressions/fuzz_8923a6787c51278e.txt` · `handwritten-pending` · `standard.gap` · `f486f3f0a237c83c`
- `c/tests/regressions/fuzz_8923a6787c51278e.uem` · `handwritten-pending` · `standard.gap` · `8923a6787c51278e`
- `c/tests/regressions/fuzz_905f95f032109533.txt` · `handwritten-pending` · `standard.gap` · `f84c232bbe451552`
- `c/tests/regressions/fuzz_905f95f032109533.uem` · `handwritten-pending` · `standard.gap` · `905f95f032109533`
- `c/tests/regressions/fuzz_971975d7b0a444ce.txt` · `handwritten-pending` · `standard.gap` · `894c038b0e799513`
- `c/tests/regressions/fuzz_971975d7b0a444ce.uem` · `handwritten-pending` · `standard.gap` · `971975d7b0a444ce`
- `c/tests/regressions/fuzz_98c8cdf0374a5bc0.txt` · `handwritten-pending` · `standard.gap` · `2ff898314a291007`
- `c/tests/regressions/fuzz_98c8cdf0374a5bc0.uem` · `handwritten-pending` · `standard.gap` · `98c8cdf0374a5bc0`
- `c/tests/regressions/fuzz_9aa113af1423cc71.txt` · `handwritten-pending` · `standard.gap` · `df40f8970ac8a357`
- `c/tests/regressions/fuzz_9aa113af1423cc71.uem` · `handwritten-pending` · `standard.gap` · `9aa113af1423cc71`
- `c/tests/regressions/fuzz_a13305f1979c0509.txt` · `handwritten-pending` · `standard.gap` · `4a6fda8204a1b63c`
- `c/tests/regressions/fuzz_a13305f1979c0509.uem` · `handwritten-pending` · `standard.gap` · `a13305f1979c0509`
- `c/tests/regressions/fuzz_a338373eb4bf51d4.txt` · `handwritten-pending` · `standard.gap` · `e111267d80f93d6c`
- `c/tests/regressions/fuzz_a338373eb4bf51d4.uem` · `handwritten-pending` · `standard.gap` · `a338373eb4bf51d4`
- `c/tests/regressions/fuzz_a3604298a65d1ad5.txt` · `handwritten-pending` · `standard.gap` · `3d343fbf2976937e`
- `c/tests/regressions/fuzz_a3604298a65d1ad5.uem` · `handwritten-pending` · `standard.gap` · `a3604298a65d1ad5`
- `c/tests/regressions/fuzz_af607e09699a13d9.txt` · `handwritten-pending` · `standard.gap` · `20431a040dcf4d16`
- `c/tests/regressions/fuzz_af607e09699a13d9.uem` · `handwritten-pending` · `standard.gap` · `af607e09699a13d9`
- `c/tests/regressions/fuzz_b41edab3ba1c6702.txt` · `handwritten-pending` · `standard.gap` · `6057382d54f251d6`
- `c/tests/regressions/fuzz_b41edab3ba1c6702.uem` · `handwritten-pending` · `standard.gap` · `b41edab3ba1c6702`
- `c/tests/regressions/fuzz_b549930f3dfa14b3.txt` · `handwritten-pending` · `standard.gap` · `ccdf349e4b76444d`
- `c/tests/regressions/fuzz_b549930f3dfa14b3.uem` · `handwritten-pending` · `standard.gap` · `b549930f3dfa14b3`
- `c/tests/regressions/fuzz_bbf427db6ff2ba6f.txt` · `handwritten-pending` · `standard.gap` · `b7034ea6732fd48b`
- `c/tests/regressions/fuzz_bbf427db6ff2ba6f.uem` · `handwritten-pending` · `standard.gap` · `bbf427db6ff2ba6f`
- `c/tests/regressions/fuzz_bf0b38d75c192f1f.txt` · `handwritten-pending` · `standard.gap` · `3ed38b9d3304c91e`
- `c/tests/regressions/fuzz_bf0b38d75c192f1f.uem` · `handwritten-pending` · `standard.gap` · `bf0b38d75c192f1f`
- `c/tests/regressions/fuzz_c62331bf727d79de.txt` · `handwritten-pending` · `standard.gap` · `92b1fa13aa98b63f`
- `c/tests/regressions/fuzz_c62331bf727d79de.uem` · `handwritten-pending` · `standard.gap` · `c62331bf727d79de`
- `c/tests/regressions/fuzz_c644e6c69a320735.txt` · `handwritten-pending` · `standard.gap` · `53f1a5eebb1456a9`
- `c/tests/regressions/fuzz_c644e6c69a320735.uem` · `handwritten-pending` · `standard.gap` · `c644e6c69a320735`
- `c/tests/regressions/fuzz_c7e7f87ea67141c8.txt` · `handwritten-pending` · `standard.gap` · `f0d662cdcea499f5`
- `c/tests/regressions/fuzz_c7e7f87ea67141c8.uem` · `handwritten-pending` · `standard.gap` · `c7e7f87ea67141c8`
- `c/tests/regressions/fuzz_c80d2cb02102f417.txt` · `handwritten-pending` · `standard.gap` · `bfaa4d4a6d7d5bb8`
- `c/tests/regressions/fuzz_c80d2cb02102f417.uem` · `handwritten-pending` · `standard.gap` · `c80d2cb02102f417`
- `c/tests/regressions/fuzz_ca321bb6acfeae09.txt` · `handwritten-pending` · `standard.gap` · `d7fcdf8ed4d5366e`
- `c/tests/regressions/fuzz_ca321bb6acfeae09.uem` · `handwritten-pending` · `standard.gap` · `ca321bb6acfeae09`
- `c/tests/regressions/fuzz_cb7bc8174a35ecf4.txt` · `handwritten-pending` · `standard.gap` · `f9566f267984620d`
- `c/tests/regressions/fuzz_cb7bc8174a35ecf4.uem` · `handwritten-pending` · `standard.gap` · `cb7bc8174a35ecf4`
- `c/tests/regressions/fuzz_d025dfc3c30ceb79.txt` · `handwritten-pending` · `standard.gap` · `e841b774b195bd12`
- `c/tests/regressions/fuzz_d025dfc3c30ceb79.uem` · `handwritten-pending` · `standard.gap` · `d025dfc3c30ceb79`
- `c/tests/regressions/fuzz_d3f4f1f0ac3ec95a.txt` · `handwritten-pending` · `standard.gap` · `ccb7559aea69e36c`
- `c/tests/regressions/fuzz_d3f4f1f0ac3ec95a.uem` · `handwritten-pending` · `standard.gap` · `d3f4f1f0ac3ec95a`
- `c/tests/regressions/fuzz_d604186d7a51770c.txt` · `handwritten-pending` · `standard.gap` · `78a4c280b275b059`
- `c/tests/regressions/fuzz_d604186d7a51770c.uem` · `handwritten-pending` · `standard.gap` · `d604186d7a51770c`
- `c/tests/regressions/fuzz_d8f44c7e27055f8a.txt` · `handwritten-pending` · `standard.gap` · `80c3204722218142`
- `c/tests/regressions/fuzz_d8f44c7e27055f8a.uem` · `handwritten-pending` · `standard.gap` · `d8f44c7e27055f8a`
- `c/tests/regressions/fuzz_dbc92cb69ac41aa9.txt` · `handwritten-pending` · `standard.gap` · `7a17065c274d9d50`
- `c/tests/regressions/fuzz_dbc92cb69ac41aa9.uem` · `handwritten-pending` · `standard.gap` · `dbc92cb69ac41aa9`
- `c/tests/regressions/fuzz_e63eb4ea174bfad6.txt` · `handwritten-pending` · `standard.gap` · `7cf94c5a5fc3df88`
- `c/tests/regressions/fuzz_e63eb4ea174bfad6.uem` · `handwritten-pending` · `standard.gap` · `e63eb4ea174bfad6`
- `c/tests/regressions/fuzz_e6d3e0a231fc79d6.txt` · `handwritten-pending` · `standard.gap` · `288b962cdc0874f0`
- `c/tests/regressions/fuzz_e6d3e0a231fc79d6.uem` · `handwritten-pending` · `standard.gap` · `e6d3e0a231fc79d6`
- `c/tests/regressions/fuzz_e6ee76e3e9a2355a.txt` · `handwritten-pending` · `standard.gap` · `edcd256c2ebaabdb`
- `c/tests/regressions/fuzz_e6ee76e3e9a2355a.uem` · `handwritten-pending` · `standard.gap` · `e6ee76e3e9a2355a`
- `c/tests/regressions/fuzz_ed794668c4794827.txt` · `handwritten-pending` · `standard.gap` · `fbf1f30c175111af`
- `c/tests/regressions/fuzz_ed794668c4794827.uem` · `handwritten-pending` · `standard.gap` · `ed794668c4794827`
- `c/tests/regressions/fuzz_ee7a38e6d1644e98.txt` · `handwritten-pending` · `standard.gap` · `449200eff6c7bb4a`
- `c/tests/regressions/fuzz_ee7a38e6d1644e98.uem` · `handwritten-pending` · `standard.gap` · `ee7a38e6d1644e98`
- `c/tests/regressions/fuzz_f1500aca4ec7d693.txt` · `handwritten-pending` · `standard.gap` · `50d903e7469f4db0`
- `c/tests/regressions/fuzz_f1500aca4ec7d693.uem` · `handwritten-pending` · `standard.gap` · `f1500aca4ec7d693`
- `c/tests/regressions/fuzz_f76cd3ca9c868504.txt` · `handwritten-pending` · `standard.gap` · `ece2114a8eb33929`
- `c/tests/regressions/fuzz_f76cd3ca9c868504.uem` · `handwritten-pending` · `standard.gap` · `f76cd3ca9c868504`
- `c/tests/regressions/fuzz_f9f43333c21e7902.txt` · `handwritten-pending` · `standard.gap` · `371d74cf1732450a`
- `c/tests/regressions/fuzz_f9f43333c21e7902.uem` · `handwritten-pending` · `standard.gap` · `f9f43333c21e7902`
- `c/tests/regressions/fuzz_fba78542581fc2eb.txt` · `handwritten-pending` · `standard.gap` · `9231ac862dc0aadd`
- `c/tests/regressions/fuzz_fba78542581fc2eb.uem` · `handwritten-pending` · `standard.gap` · `fba78542581fc2eb`
- `c/tests/regressions/fuzz_fdf7eb059283fdb7.txt` · `handwritten-pending` · `standard.gap` · `2be789637445382d`
- `c/tests/regressions/fuzz_fdf7eb059283fdb7.uem` · `handwritten-pending` · `standard.gap` · `fdf7eb059283fdb7`
- `c/tests/vectors/bad_magic.uem` · `handwritten-pending` · `standard.gap` · `0ff64a815f69820e`
- `c/tests/vectors/trailing.uem` · `handwritten-pending` · `standard.gap` · `88ab7520c9152174`
- `c/tests/vectors/truncated.uem` · `handwritten-pending` · `standard.gap` · `33870149c489e383`
- `c/tests/vectors/unknown_opcode.uem` · `handwritten-pending` · `standard.gap` · `9bef076d238d33a9`
- `c/third_party/cJSON.c` · `external-vendored` · `ok` · `75c51de8fa40ac9d`
- `c/third_party/cJSON.h` · `external-vendored` · `ok` · `0578cc29132912ed`
- `c/third_party/sha256.c` · `external-vendored` · `ok` · `7512aca9136ce6e2`
- `c/third_party/sha256.h` · `external-vendored` · `ok` · `ee296ea123f062e6`
- `coverage.json` · `evidence` · `ok` · `9f99a1a762f30289`
- `coverage_py.json` · `evidence` · `ok` · `d2ba6d0c467789e7`
- `docs/DEVELOPER_WORKFLOW.md` · `handwritten-pending` · `standard.gap` · `5ce70a955dc69a2c`
- `examples/declarations/invoice_total.py` · `handwritten-pending` · `standard.gap` · `d0cb833aace2a12a`
- `examples/declarations/text_stats_program.py` · `handwritten-pending` · `standard.gap` · `d9d565c596a5efdd`
- `examples/declarations/text_stats_v2.py` · `handwritten-pending` · `standard.gap` · `0c083c7704d22e8d`
- `examples/one_dimension.py` · `handwritten-pending` · `standard.gap` · `48d90d21a1e77ced`
- `examples/three_dimensions.py` · `handwritten-pending` · `standard.gap` · `a5bc88a92e9fcf54`
- `examples/two_dimensions.py` · `handwritten-pending` · `standard.gap` · `a6eec3842bbbe930`
- `pyproject.toml` · `handwritten-pending` · `standard.gap` · `34ac92612457d845`
- `scripts/audit_standard_ten.py` · `handwritten-pending` · `standard.gap` · `400c2bdc3650a4bc`
- `scripts/clean_room_ten.sh` · `handwritten-pending` · `standard.gap` · `a25cddf4323da5c8`
- `scripts/emit_l13_report.py` · `handwritten-pending` · `standard.gap` · `3810ee0ccf9dc694`
- `scripts/run_l13.sh` · `handwritten-pending` · `standard.gap` · `0b8a95c50aeceb72`
- `scripts/run_standard_ten.sh` · `handwritten-pending` · `standard.gap` · `970611e014e21f56`
- `seed/ROOT.seed.json` · `seed` · `ok` · `bcd58991e3a7b754`
- `seed/SCHEMA.json` · `seed` · `ok` · `61776cb0433eff8b`
- `seed/SEED_SCHEMA.md` · `seed` · `ok` · `91b67ddab6a72624`
- `seed/declarations/invoice_total.json` · `seed` · `ok` · `fd1bb8733a2176c1`
- `seed/declarations/text_stats_v2.json` · `seed` · `ok` · `9b0fd8aa94ded247`
- `seed/stamps/generator.lock.json` · `seed` · `ok` · `808ad1904f00203c`
- `tests/test_benchmark.py` · `handwritten-pending` · `standard.gap` · `4ce9240b671a4c66`
- `tests/test_boundary.py` · `handwritten-pending` · `standard.gap` · `bfa6a879dfec4bd1`
- `tests/test_build_gauntlet.py` · `handwritten-pending` · `standard.gap` · `4db216ce0df2620d`
- `tests/test_clock.py` · `handwritten-pending` · `standard.gap` · `39c716bc4f3bc4df`
- `tests/test_declaration.py` · `handwritten-pending` · `standard.gap` · `bd4be62b91c9df03`
- `tests/test_dimensions.py` · `handwritten-pending` · `standard.gap` · `b2b4af310463fe7e`
- `tests/test_event_l10.py` · `handwritten-pending` · `standard.gap` · `ae2bf6cd3ee41fc7`
- `tests/test_expr.py` · `handwritten-pending` · `standard.gap` · `1cb5e1ff6866d5f9`
- `tests/test_generator.py` · `handwritten-pending` · `standard.gap` · `5455ca54048d663e`
- `tests/test_invariants.py` · `handwritten-pending` · `standard.gap` · `2747eda479b3b5f6`
- `tests/test_l11.py` · `handwritten-pending` · `standard.gap` · `b44ba8f257eb3915`
- `tests/test_l13.py` · `handwritten-pending` · `standard.gap` · `6b482865ece5dd24`
- `tests/test_l13_coverage.py` · `handwritten-pending` · `standard.gap` · `10b726d541f918ec`
- `tests/test_l13_deep.py` · `handwritten-pending` · `standard.gap` · `f2a67de935d2ae1f`
- `tests/test_signature.py` · `handwritten-pending` · `standard.gap` · `8e640c56a6580c13`
- `tests/test_standard_ten.py` · `handwritten-pending` · `standard.gap` · `6daf6aec6921f2df`
- `tests/test_uem.py` · `handwritten-pending` · `standard.gap` · `31b618bbe72e2cb1`
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
- `unified/generator/cli.py` · `handwritten-pending` · `standard.gap` · `ce2200eb342577af`
- `unified/generator/declaration.py` · `handwritten-pending` · `standard.gap` · `63372f8abe8918a9`
- `unified/generator/event_emit.py` · `handwritten-pending` · `standard.gap` · `7d151b2e1fb6db0f`
- `unified/generator/expr.py` · `handwritten-pending` · `standard.gap` · `3e0971d83229403c`
- `unified/generator/expr_emit.py` · `handwritten-pending` · `standard.gap` · `d01abd88a13899e7`
- `unified/generator/gauntlet.py` · `handwritten-pending` · `standard.gap` · `8069ffa90df103c2`
- `unified/generator/generate.py` · `handwritten-pending` · `standard.gap` · `e2f992740b0ee252`
- `unified/generator/names.py` · `handwritten-pending` · `standard.gap` · `04791c2fa1ca7cf6`
- `unified/generator/render.py` · `handwritten-pending` · `standard.gap` · `c7d4a443dead9e30`
- `unified/generator/render_declared.py` · `handwritten-pending` · `standard.gap` · `3c3ecca285f37825`
- `unified/generator/validate.py` · `handwritten-pending` · `standard.gap` · `8fb3436cc6088a28`
- `unified/generator/verify_plan.py` · `handwritten-pending` · `standard.gap` · `0e981d8721b784e0`
- `unified/generator/write_fs.py` · `handwritten-pending` · `standard.gap` · `57e811ec50762428`
- `unified/machine/__init__.py` · `handwritten-pending` · `standard.gap` · `a214cc6bcfe02875`
- `unified/machine/bytecode.py` · `handwritten-pending` · `standard.gap` · `0a7fa4266ec8f067`
- `unified/machine/canonical.py` · `handwritten-pending` · `standard.gap` · `2ac4fcb9339e5116`
- `unified/machine/compile_decl.py` · `handwritten-pending` · `standard.gap` · `4264315a13b6bb48`
- `unified/machine/gauntlet.py` · `handwritten-pending` · `standard.gap` · `910d737cd1cecc3f`
- `unified/machine/host.py` · `physical-host-boundary` · `ok` · `46a70046d13b66d1`
- `unified/machine/interpreter.py` · `handwritten-pending` · `standard.gap` · `123e5d0bd4804636`
- `unified/machine/l11.py` · `handwritten-pending` · `standard.gap` · `692df24ba44d2fdc`
- `unified/machine/l13.py` · `handwritten-pending` · `standard.gap` · `3b685965e815a0c7`
- `unified/machine/l13_catalog.py` · `handwritten-pending` · `standard.gap` · `3379096736877fef`
- `unified/machine/measure.py` · `handwritten-pending` · `standard.gap` · `f6c3bd6f8b340780`
- `unified/machine/opcodes.py` · `handwritten-pending` · `standard.gap` · `97cc810a83ccc046`
- `unified/machine/primitives.py` · `handwritten-pending` · `standard.gap` · `aa9cab92faacade8`
- `unified/machine/thing.py` · `handwritten-pending` · `standard.gap` · `991b7864294015f9`
- `unified/machine/validate.py` · `handwritten-pending` · `standard.gap` · `a7233a9e4015f04f`
- `unified/standard.py` · `handwritten-pending` · `standard.gap` · `8aa45f56d2948ac5`
- `unified/standard_audit.py` · `handwritten-pending` · `standard.gap` · `070c1e4ce5cb1f28`
- `unified/standard_generate.py` · `handwritten-pending` · `standard.gap` · `78fd6e444cffdc5d`
- `unified/thing.py` · `handwritten-pending` · `standard.gap` · `7db7669dc8e629b1`
- `unified/verify.py` · `handwritten-pending` · `standard.gap` · `d72f0665fb484a42`
